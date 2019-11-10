var endpoint;
var key;
var authSecret;
var alreadySubscribed = false; 

var signalById = {};
var player = null;

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
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
  var rawKey = subscription.getKey ? subscription.getKey('p256dh') : '';
  key = rawKey ?
        btoa(String.fromCharCode.apply(null, new Uint8Array(rawKey))) : '';
  var rawAuthSecret = subscription.getKey ? subscription.getKey('auth') : '';
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
    var x = document.getElementById("topNav");
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
	var signal = signalById[sound.id];
	var data = {"url": signal["url"], "_xsrf": getCookie("_xsrf")};
	$('#speaker').show();
    $.post('/sounds', data).done(function (msg) {$('#speaker').hide();}).fail(function () {
    	alert('cannot play sound');
    	$('#speaker').hide();
    });
}

function getStream(source) {
	if (player !== null) {
		player.destroy();
	}
	signal = signalById[source.id];
	$('#camdata').show();
	var canvas = document.getElementById('camdata');
	var ctx = canvas.getContext('2d');
	ctx.fillStyle = '#444';
	ctx.fillText('Loading...', canvas.width/2-30, canvas.height/3);
	// Setup the WebSocket connection and start the player
	var url = 'wss://' + window.location.hostname + ':' + window.location.port + '/video?url=' + signal["url"];
	player = new JSMpeg.Player(url, {canvas: canvas, disableGl: true});
}

function sensors() {
	$.get('/sensors', function (data) {
		handleActiveMenu('sensors');
		var html = "";
		for (var i=0;i<data['sensors'].length;i++) {
			var se = data['sensors'][i];
			signalById[se['id']] = se;
			html += '<div class="signal">'
			html += '<span id="' + se['id'] + '">' + se['name'] + '</span>';
			html +='<span class="sensor">'
			if (se['value'].indexOf(',') > -1) {
				var parts = se['value'].split(',');
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
		var html = "";
		for (var i=0;i<data['switches'].length;i++) {
			var sw = data['switches'][i];
			signalById[sw['id']] = sw;
			html += '<div class="signal">'
			html += '<span id="' + sw['id'] + '">' + sw['name'] + '</span>';
			html += '<label class="switch"><input type="checkbox" id="' + sw['id'] + '"';
			if (sw['value'] === true) {
				html += ' checked';
			}
			html +='><span class="slider round"></span></label>';
			html += '</div>';
		}
		$('#content').html(html);
	});
}

function sounds() {
	$.get('/sounds', function (data) {
		handleActiveMenu('sounds');
		var html = "";
		for (var i=0;i<data['sounds'].length;i++) {
			var so = data['sounds'][i];
			signalById[so['id']] = so;
			html += '<div class="signal">';
			html += '<span id="' + so['id'] + '">' + so['name'] + '</span>';
			html += '<img src="/alfred/static/static/img/speaker.png" id="' + so['id'] + '" onclick="playSound(this)">';
			html += '</div>';
		}
		$('#content').html(html);
	});
}

function cameras() {
	$.get('/cameras', function (data) {
		handleActiveMenu('cameras');
		var html = "";
		for (var i=0;i<data['cameras'].length;i++) {
			var ca = data['cameras'][i];
			signalById[ca['id']] = ca;
			html += '<div class="signal">';
			html += '<span id="' + ca['id'] + '">' + ca['name'] + '</span>';
			html += '<img src="/alfred/static/static/img/video.png" id="' + ca['id'] + '" onclick="getStream(this)">';
			html += '</div>';
		}
		$('#content').html(html);
	});
}

$(document).ready(function() {
	$(document).on('click', 'input:checkbox', function(event) {
	    // this will contain a reference to the checkbox
		data = {'sid': this.id, 'url': signalById[this.id]['url'], 'state': 0};
		data['_xsrf'] = getCookie("_xsrf");
	    if (this.checked) {
	        data['state'] = 1;
	    }
	    $.post('/switches', data).done(function (msg) {}).fail(function () {
	    	alert('cannot toggle');
	    });
	});
	$(document).on('click', '#camdata', function(event) {
		player.destroy();
		player = null;
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
