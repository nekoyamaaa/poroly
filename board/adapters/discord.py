import json

import discord

from my.discordmod import Client

class Bot(Client):
    REACTION = '✅'
    REQUIRED_PERMISSIONS = [
        'view_channel', 'manage_channels',
        'read_message', 'send_messages', 'read_message_history',
        'add_reactions'
    ]
    CHANNEL_NAME = 'マルチ募集'

    async def on_ready(self):
        if not getattr(self, 'board_url', None):
            raise ValueError('board_url is not set')

        if self.master:
            await self.master.create_dm()
            await self.cleanup(self.master.dm_channel)

        for guild in self.guilds:
            await self.prepare(guild)
        self.logger.info(
            'Successfully logged in as %s.  Invitation: %s',
            self.user.name,
            self.invite_url
        )

    async def on_guild_join(self, guild):
        self.logger.info('Bot joined to %s', guild)
        await self.prepare(guild)

    async def on_message(self, message):
        if not self.is_target(message):
            return

        if (self.user.mentioned_in(message) or self.role_mentioned_in(message)) and \
           'url' in message.content.lower():
            await self.usage(message=message)
            return

        data = self.extract_data(message)
        if not data:
            return
        if data.get('error'):
            await self.reply(message, data['error'])
        else:
            try:
                data = self.manager.validate(data)
                response = self.manager.save(data)
            except ValueError as ex:
                await self.reply(message, str(ex))
            else:
                created = json.loads(response).get('data')[0]
                await self.on_board_save(message, created)

    async def on_board_save(self, message, saved):
        await message.add_reaction(self.REACTION)
        completed_message = self.manager.report_for("saved", saved)
        if completed_message:
            await self.reply(message, completed_message)

    async def on_message_delete(self, message):
        if not self.is_target(message):
            return
        if not [reaction for reaction in message.reactions if reaction.me]:
            return

        data = self.extract_data(message)
        if not data:
            return

        self.manager.destroy(data)

    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return

        await after.remove_reaction(self.REACTION, self.user)
        await self.on_message(after)

    async def usage(self, message=None, channel=None):
        if not message and not channel:
            raise ValueError('either message or channel required')
        if not channel:
            channel = message.channel
        board_url = getattr(self, 'board_url', None)
        # Although check existence in `on_ready`, for more stability
        if board_url:
            msg = '\n'.join([
                '掲示板サーバーのURLは',
                '<{0}>',
                'このDiscordサーバーの募集だけ見る場合は',
                '<{0}?guild={1}>',
            ]).format(
                self.board_url, channel.guild.id
            )
        else:
            msg = '掲示板サーバーのURLが設定されていません。'
            msg += 'お手数ですがボットの管理者までお知らせください。'

        if message:
            await self.reply(message, msg)
        else:
            await channel.send(msg)

    def extract_data(self, message):
        content = message.clean_content.replace('@' + self.user.name, '')
        result = self.manager.parse(content, message)
        if not result:
            return None
        if result.get('error'):
            return result

        result.update({
            'owner': {
                'id': message.author.id,
                'name': message.author.display_name,
            },
            'guild': {
                'id': message.channel.guild.id,
                'name': message.channel.guild.name
            },
            'time': message.edited_at or message.created_at
        })
        return result

    @property
    def channel_name(self):
        # TODO: i18n or make configurable
        return self.CHANNEL_NAME

    @property
    def description(self):
        return (getattr(self, '_description', None) or "").format(
            channel=self.channel_name,
            reaction=self.REACTION
        )

    @description.setter
    def description(self, value):
        self._description = str(value) if value else None

    def role_mentioned_in(self, message):
        for role in message.role_mentions:
            if role in message.channel.guild.me.roles:
                return True
        return False

    def is_target(self, message):
        if message.author.bot or message.author.system:
            return False

        if message.mentions and not self.user.mentioned_in(message):
            self.logger.debug('The message is for others')
            return False
        if message.role_mentions and not self.role_mentioned_in(message):
            self.logger.debug('The message is for other roles')
            return False

        if not hasattr(message.channel, 'guild') or not message.channel.guild:
            self.logger.debug('%s does not have guild.', message.channel)
            return False

        return message.channel.name == self.channel_name

    async def prepare(self, guild):
        channel = discord.utils.find(lambda c: c.name == self.channel_name, guild.channels)
        if channel:
            return
        try:
            channel = await guild.create_text_channel(self.channel_name)
        except discord.errors.Forbidden:
            self.logger.error(
                'Could not create my channel in %s, will notify to %s',
                guild, guild.owner
            )
            await guild.owner.send(
                '権限不足でサーバー「{guild}」にチャンネルを作れませんでした。招待をやり直してください。 <{url}>'.format(
                    guild=guild.name, url=self.invite_url)
            )

        await channel.send(self.description)
        await self.usage(channel=channel)

    @property
    def description(self):
        return (
            self.manager.decription +
            """\n掲示板サーバーへの書き込みが完了するとボットがリアクション{reaction}をつけてリプライでもお知らせします。
部屋番号が含まれない投稿や他人宛のメンションは無視します。"""
        ).format(
            channel=self.channel_name,
            reaction=self.REACTION
        )
