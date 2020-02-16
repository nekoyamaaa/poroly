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
        if self.master:
            await self.master.create_dm()
            await self.cleanup(self.master.dm_channel)
        for guild in self.guilds:
            await self.prepare(guild)

    async def on_guild_join(self, guild):
        self.logger.info('Bot joined to %s', guild)
        await self.prepare(guild)

    async def on_message(self, message):
        if not self.is_target(message):
            return

        data = self.extract_data(message)
        if not data:
            return
        if data.get('error'):
            await self.reply(message, data['error'])
        else:
            try:
                response = self.manager.save(data)
            except ValueError as ex:
                await self.reply(message, str(ex))
            else:
                created = json.loads(response).get('data')[0]
                await self.on_board_save(message, created)

    async def on_board_save(self, message, saved):
        await message.add_reaction(self.REACTION)
        completed_message = self.user_notification("saved", saved)
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

    def extract_data(self, message):
        result = self.parse_content(message.content, message=message)
        if not result:
            return None
        if result.get('warning'):
            return result

        result.update({
            'owner': {
                'id': message.author.id,
                'name': message.author.display_name,
            },
            'guild': message.channel.guild.name,
            'time': message.edited_at or message.created_at
        })
        return result

    def parse_content(self, content, message=None):
        raise NotImplementedError()

    def user_notification(self, action, obj=None):
        if action == "saved" and obj.get('message'):
            return "`{}`として投稿しました".format(obj.get('message'))

    @property
    def channel_name(self):
        # TODO: i18n
        return self.CHANNEL_NAME

    @property
    def description(self):
        return (self._description or "").format(
            channel=self.channel_name,
            reaction=self.REACTION
        )

    @description.setter
    def description(self, value):
        self._description = str(value) if value else None

    def is_target(self, message):
        if message.author.bot or message.author.system:
            return False

        if not hasattr(message.channel, 'guild') or not message.channel.guild:
            self.logger.info('%s does not have guild.', message.channel)
            return False

        return message.channel.name == self.channel_name

    async def prepare(self, guild):
        channel = discord.utils.find(lambda c: c.name == self.CHANNEL_NAME, guild.channels)
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
