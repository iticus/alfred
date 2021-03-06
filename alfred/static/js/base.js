let endpoint;
let key;
let authSecret;
let alreadySubscribed = false;

let signalById = {};
let streamActive = false;
let player = null;
let socket = null;

function getCookie(name) {
    let r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

function ws_proto() {
	return location.protocol.match(/^https/) ? "wss://" : "ws://";
}

function urlB64ToUint8Array(base64String) {
	  const padding = '='.repeat((4 - base64String.length % 4) % 4);
	  const base64 = (base64String + padding)
	    .replace(/\-/g, '+')
	    .replace(/_/g, '/');

	  const rawData = window.atob(base64);
	  const outputArray = new Uint8Array(rawData.length);

	  for (let i = 0; i < rawData.length; ++i) {
	    outputArray[i] = rawData.charCodeAt(i);
	  }
	  return outputArray;
	}

navigator.serviceWorker.register('/service-worker.js')
.then(function(registration) {
  return registration.pushManager.getSubscription()
  .then(function(subscription) {
    if (subscription) {
      alreadySubscribed = true;
      return subscription;
    }
    return registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8Array(window.vapidPublicKey)});
  });
}).then(function(subscription) {
  if (alreadySubscribed) {
	  return
  }

  let rawKey = subscription.getKey ? subscription.getKey('p256dh') : '';
  key = rawKey ?
        btoa(String.fromCharCode.apply(null, new Uint8Array(rawKey))) : '';
  let rawAuthSecret = subscription.getKey ? subscription.getKey('auth') : '';
  authSecret = rawAuthSecret ? btoa(String.fromCharCode.apply(null, new Uint8Array(rawAuthSecret))) : '';
  endpoint = subscription.endpoint;
  
  fetch('/subscribe', {
    method: 'post',
    credentials: 'include',
    headers: {
      'Content-type': 'application/json',
      'X-XSRFToken': getCookie("_xsrf")
    },
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      key: key,
      authSecret: authSecret,
    }),
  });
});

function topNav() {
    let x = document.getElementById("topNav");
    if (x.className === "topnav") {
        x.className += " responsive";
    } else {
        x.className = "topnav";
    }
}

function handleActiveMenu(text) {
	$('#topNav a').each( function () {
		if (this.text.toLowerCase() === text.toLowerCase()) {
			$(this).css('background-color', '#17a2b8');
		}
		else {
			$(this).css('background-color', '#343a40');
		}
	});
	$('.topnav').removeClass('responsive');
}

function playSound(sound) {
	let signal = signalById[sound.id];
	let data = {"url": signal["url"], "_xsrf": getCookie("_xsrf")};
	$('#speaker').show();
    $.post('/sounds', data).done(function (msg) {$('#speaker').hide();}).fail(function () {
    	alert('cannot play sound');
    	$('#speaker').hide();
    });
}

function getStream(source) {
	if (player !== null) {
		player.destroy();
		player = null;
	}
	if (socket !== null) {
		socket.close();
		socket = null;
	}
	let signal = signalById[source.id];
	let canvas = document.getElementById('camdata');
	let ctx = canvas.getContext('2d');
	ctx.fillStyle = '#444';
	ctx.fillText('Loading...', canvas.width / 2 - 30, canvas.height / 3);
	$('#camdata').show();
	if (signal["attributes"].hasOwnProperty("type") && signal["attributes"]["type"] == "image") {
		let upstream_proto = "http";
		if (signal["attributes"].hasOwnProperty("proto")) {
			upstream_proto = signal["attributes"]["proto"];
		}
		let url = '/' + upstream_proto + '_video?url=' + signal["url"];
		socket = new WebSocket(ws_proto() + window.location.hostname + ':' + window.location.port + url);
		socket.binaryType = 'arraybuffer';
		socket.onopen = function () {
			streamActive = true;
			socket.send('?');
		};
		socket.onclose = () => {
            console.log('websocket connection closed by server');
        };
		socket.onmessage = function (msg) {
			if (msg.length === 0) {
				return setTimeout(function() {
					socket.send('?');
				}, 100);
			}
			let blob  = new Blob([msg.data], {type: "image/jpeg"});
			let img = new Image();
			img.onload = function (e) {
				ctx.drawImage(img, 0, 0);
				window.URL.revokeObjectURL(img.src);
				if (canvas.width !== img.width) {
					canvas.width = img.width;
				}
				if (canvas.height !== img.height) {
					canvas.height = img.height;
				}
				img = null;
			};
			img.onerror = img.onabort = function () {
				img = null;
				socket.close();
			};
			img.src = window.URL.createObjectURL(blob);
			if (streamActive === false) {
				socket.send("!");
				return;
			}
			socket.send('?');
		};
	}
	else {
		// Setup the WebSocket connection and start the player
		let url = ws_proto() + window.location.hostname + ':' + window.location.port + '/ws_video?url=' + signal["url"];
		player = new JSMpeg.Player(url, {canvas: canvas, disableGl: true});
	}
}

function sensors() {
	$.get('/sensors', function (data) {
		handleActiveMenu('sensors');
		let html = "";
		for (let i=0;i<data['sensors'].length;i++) {
			let se = data['sensors'][i];
			signalById[se['id']] = se;
			html += '<div class="signal">';
			html += '<span id="' + se['id'] + '">' + se['name'] + '</span>';
			html +='<span class="sensor">';
			if (se['value'].indexOf(',') > -1) {
				let parts = se['value'].split(',');
				html += parts[0] + '&#176;C, ' + parts[1] + '% rH';
			}
			else {
				html += se['value'];
			}
			html += '</span></div>';
		}
		$('#content').html(html);
	});
}

function switches() {
	$.get('/switches', function (data) {
		handleActiveMenu('switches');
		let html = "";
		for (let i=0;i<data['switches'].length;i++) {
			let sw = data['switches'][i];
			signalById[sw['id']] = sw;
			html += '<div class="signal">';
			html += '<span id="' + sw['id'] + '">' + sw['name'] + '</span>';
			html += '<label class="switch"><input type="checkbox" id="' + sw['id'] + '"';
			if (sw['value'] === true) {
				html += ' checked';
			}
			if (sw['active'] !== 1) {
				html += ' disabled';
			}
			html += '><span class="slider round';
			if (sw['active'] !== 1) {
				html += ' disabled';
			}
			html += '"></span></label></div>';
		}
		$('#content').html(html);
	});
}

function sounds() {
	$.get('/sounds', function (data) {
		handleActiveMenu('sounds');
		let html = "";
		for (let i=0;i<data['sounds'].length;i++) {
			let so = data['sounds'][i];
			signalById[so['id']] = so;
			html += '<div class="signal">';
			html += '<span id="' + so['id'] + '">' + so['name'] + '</span>';
			html += '<img src="/static/img/speaker.png" id="' + so['id'] + '" onclick="playSound(this)">';
			html += '</div>';
		}
		$('#content').html(html);
	});
}

function cameras() {
	$.get('/cameras', function (data) {
		handleActiveMenu('cameras');
		let html = "";
		for (let i=0;i<data['cameras'].length;i++) {
			let ca = data['cameras'][i];
			signalById[ca['id']] = ca;
			html += '<div class="signal">';
			html += '<span id="' + ca['id'] + '">' + ca['name'] + '</span>';
			html += '<img src="/static/img/video.png" id="' + ca['id'] + '" onclick="getStream(this)">';
			html += '</div>';
		}
		$('#content').html(html);
	});
}

$(document).ready(function() {
	$(document).on('click', 'input:checkbox', function(event) {
	    // this will contain a reference to the checkbox
		let data = {'sid': this.id, 'url': signalById[this.id]['url'], 'state': 0};
		data['_xsrf'] = getCookie("_xsrf");
	    if (this.checked) {
	        data['state'] = 1;
	    }
	    $.post('/switches', data).done(function (msg) {}).fail(function () {
	    	alert('cannot toggle');
	    });
	});
	$(document).on('click', '#camdata', function(event) {
		streamActive = false;
		let canvas = document.getElementById('camdata');
		canvas.width = canvas.width;
		if (player !== null) {
			player.source.socket.close();
			player.source.destroy();
			player.destroy();
			player = null;
		}
		if (socket !== null) {
			socket.close();
			socket = null;
		}
		$('#camdata').hide();
	});
});

let installPromptEvent;

window.addEventListener('beforeinstallprompt', (event) => {
  // Prevent Chrome <= 67 from automatically showing the prompt
  //event.preventDefault();
  // Stash the event so it can be triggered later.
  //installPromptEvent = event;
  // Update the install UI to notify the user app can be installed
  //document.querySelector('#install-button').disabled = false;
  event.prompt();
});
