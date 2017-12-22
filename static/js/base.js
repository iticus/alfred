var signalById = {};
var streamEnabled = false;

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

function getImage(signal) {
	var dt = new Date();
	var params = {'sid': signal['id'], 'url': signal['url'], 'dt': dt.getTime()};
	$('#camdata').attr('src', '/cameras/?' + jQuery.param(params));
}

function getSnapshot(source) {
	var signal = signalById[source.id];
	getImage(signal);
	$('#camdata').show();
}

function getStream(source) {
	signal = signalById[source.id];
	streamEnabled = true;
	getImage(signal);
	$('#camdata').show();
	$("#camdata").bind("load", function() {
		if (streamEnabled) {
			setTimeout(getImage, 333, signal);
		}
		else {
			$('#camdata').off('load');
			$('#camdata').hide();
		}
	});
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

function cameras() {
	$.get('/cameras', function (data) {
		handleActiveMenu('cameras');
		var html = "";
		for (var i=0;i<data['cameras'].length;i++) {
			var ca = data['cameras'][i];
			signalById[ca['id']] = ca;
			html += '<div class="signal">';
			html += '<span id="' + ca['id'] + '">' + ca['name'] + '</span>';
			html += '<img src="/static/img/picture.png" id="' + ca['id'] + '" onclick="getSnapshot(this)">';
			html += '<img src="/static/img/video.png" id="' + ca['id'] + '" onclick="getStream(this)">';
			html += '</div>';
		}
		$('#content').html(html);
	});
}

$(document).ready(function() {
	$(document).on('click', 'input:checkbox', function(event) {
	    // this will contain a reference to the checkbox
		data = {'sid': this.id, 'url': signalById[this.id]['url'], 'state': 0};
	    if (this.checked) {
	        data['state'] = 1;
	    }
	    $.post('/switches', data).done(function (msg) {}).fail(function () {
	    	alert('cannot toggle');
	    });
	});
	$(document).on('click', '#camdata', function(event) {
		streamEnabled = false;
		$('#camdata').hide();
	});
});