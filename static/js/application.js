(function() {
"use strict";

  var connection, template, tbody, connectStatus;
  var EXPIRE_IN_MSEC = 2 * 60 * 1000;
  var NAME_MAX_LENGTH = 16;

  class Room {
    constructor(values) {
      this.values = {};
      this.fields = [
        'time', 'owner', 'guild',
        'id', 'message',
        'type', 'difficulty', 'rule',
        'slots'
      ];
      for (let name of this.fields) {
        this.values[name] = this.clean(name, values[name]);
      }
    }
    get html_id() {
      return 'room-' + this.values.id;
    }
    is_closed() {
      return this.values.slots == 0;
    }
    is_expired() {
      return this.values.time !== undefined && (Date.now() - this.values.time) > EXPIRE_IN_MSEC;
    }
    is_active() {
      return ! this.is_closed() && ! this.is_expired();
    }
    clean(name, value) {
      if ( value === undefined ) return value;
      switch(name) {
        case 'id':
          value = value.toString();
          break;
        case 'slots':
          value = Number(value);
          break;
        case 'time':
          var d = new Date(0);
          if ( isNaN(d.setUTCSeconds(Number(value))) )
            return;
          value = d;
          break;
        case 'owner':
        case 'guild':
          if ( value.name == undefined )
            value.name = '';
          break;
      }
      return value;
    }
    humanize(name) {
      let value = this.values[name];
      if ( value === undefined ) return '';
      switch(name) {
        case 'id':
          value = `${value.slice(0,3)}-${value.slice(3,8)}`;
          break;
        case 'slots':
          if ( value == 0 ) {
            value = '〆';
          } else {
            value = `@${value}`;
          }
          break;
        case 'time':
          value = value.toLocaleTimeString();
          break;
        case 'owner':
          value = value.name;
          if (value.length > NAME_MAX_LENGTH)
            value = value.slice(0, NAME_MAX_LENGTH) + "…";
          break;
        case 'guild':
          value = value.name;
          if (value.length > NAME_MAX_LENGTH)
            value = value.slice(0, NAME_MAX_LENGTH) + "…";
          value = '@' + value;
          break;
      }
      return value;
    }
    remove() {
      var row = document.getElementById(this.html_id);
      if ( row ) row.remove();
    }
    render() {
      var row = document.getElementById(this.html_id);
      var newcomer = false;
      var match = null;
      if ( ! row ) {
        newcomer = true;
        row = template.cloneNode(true);
        row.id = this.html_id;
      }
      for ( let name of this.fields ) {
        if ( this.values[name] === undefined ) continue;
        let target = row.querySelector(`[name='room-${name}']`);
        target.textContent = this.humanize(name);
        switch(name){
          case 'owner':
          case 'guild':
            target.setAttribute('data-id', this.values[name].id);
            target.setAttribute('title', this.values[name].name);
            break;
          case 'time':
            target.setAttribute('datetime', this.values.time.toISOString());
            break;
        }
        if ( window.filter && window.filter.has(name) ) {
          if ( window.filter.get(name) == ( this.values[name].id || this.values[name] ) ) {
            match = true;
          }
        }
      }
      if ( window.filter ) {
          row.setAttribute('data-filter', match ? 'match' : 'unmatch');
      }
      row.setAttribute('data-closed', this.is_closed());
      row.setAttribute('data-expired', this.is_expired());
      if ( newcomer || this.is_active() ) {
        tbody.insertBefore(row, tbody.firstElementChild);
      }
    }
    static delete_all() {
      while (tbody.firstChild != template) {
        tbody.firstChild.remove();
      }
    }
    static cleanup() {
      for ( let tr of tbody.getElementsByTagName('tr') ) {
        if ( tr == template ) continue;
        let trTime = Date.parse(tr.getElementsByTagName('time')[0].dateTime);

        if ( (Date.now() - trTime) > EXPIRE_IN_MSEC ) {
          tr.remove();
        }
      }
    }
  }
  function connect(endpoint) {
    var serverUrl;
    var scheme = "ws";

    if (document.location.protocol === "https:") {
      scheme += "s";
    }
    serverUrl = scheme + ':' + endpoint;
    connection = new ReconnectingWebSocket(serverUrl);

    connection.onopen = function(evt) {
      console.info('Successfully connected to Board server.');
      connectStatus.className = 'success';
      if ( ! window.polling ) {
        window.polling = setInterval(function(){
          if ( connection.readyState == WebSocket.OPEN )
            connection.send('ping');
        }, 30*1000);
      }
    };
    connection.onclose = function(evt) {
      connectStatus.className = 'danger';
    };

    connection.onmessage = function(evt) {
      var message;
      try {
        message = JSON.parse(evt.data);
      } catch(e) {
        console.error('Could not parse received data.');
        console.dir(evt.data);
        return;
      }

      var room;
      if ( message.type == 'all' ) {
        Room.delete_all();
      } else if ( message.type == 'delete') {
        for ( let data of message.data ) {
          room = new Room(data);
          room.remove();
        }
        return;
      }
      for ( let data of message.data ) {
        room = new Room(data);
        room.render();
      }
    };
  }
  document.addEventListener("DOMContentLoaded", function(){
    if ( window.location.search ) {
      window.filter = new URLSearchParams(window.location.search);
      document.body.className += " filtered";
    }
    if (window.boardServer)
      connect(window.boardServer);
    template = document.getElementById('room-template');
    tbody = template.parentNode;
    connectStatus = document.getElementById('connect-status');
    if (window.expireSec) {
      EXPIRE_IN_MSEC = window.expireSec * 1000;
    }
    window.cleaner = setInterval(Room.cleanup, EXPIRE_IN_MSEC/2);
  });
})();
