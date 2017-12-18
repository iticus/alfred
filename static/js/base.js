var signalById = {};

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
			html += '<img src="/static/img/picture.png" id="' + ca['id'] + '">';
			html += '<img src="/static/img/video.png" id="' + ca['id'] + '">';
			html += '</div>';
		}
		$('#content').html(html);
	});
}

function about() {
	handleActiveMenu('about');
	$('#content').html('About me ...');
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
});