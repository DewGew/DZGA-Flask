
async function requestAPI(url){
	const response = await fetch(flask_server + url, {
		method: 'post',
		headers: {
			'Accept': 'application/json',
			'Content-Type': 'application/json',
			'Authorization': 'Bearer '+ csrf_token
		}
	})
	const data = await response.json();

	if (data.message == 'WRONG CODE'){alert('WRONG CODE')};
	if (response.status !== 200 || data.message == 'WRONG CODE') throw Error(data.message);	
		return data;	
}

function restart(){
	requestAPI("/api?custom=restart")
	$("body").css("cursor", "wait");
	setTimeout(function(){
		location.reload();
		$("body").css("cursor", "default");
	}, 7000); // 3000 milliseconds = 3 seconds
}

function syncdevices(){
	requestAPI("/api?custom=sync")
	$("body").css("cursor", "progress");
	setTimeout(function(){
		location.reload();
		$("body").css("cursor", "default");
	}, 6000); // 3000 milliseconds = 3 seconds
}

function toogleSwitch(idx, protect){
	if (protect == 'True'){
		$('#onoffpin_' + idx).modal('show');
		
	}else{
		requestAPI("/api?type=command&param=switchlight&idx=" + idx + "&switchcmd=Toggle")
	}
}
function toogleSecSwitch(idx){
	var pin = $('#inputPin_'+idx).val();
	requestAPI("/api?type=command&param=switchlight&idx=" + idx + "&switchcmd=Toggle&passcode=" + pin)
}

function toogleGroup(idx){
	requestAPI("/api?type=command&param=switchscene&idx=" + idx + "&switchcmd=Toggle")
}
function activateScene(idx){
	requestAPI("/api?type=command&param=switchscene&idx=" + idx + "&switchcmd=On")
}
function openCloseBlind(idx, dir){
	requestAPI("/api?type=command&param=switchlight&idx=" + idx + "&switchcmd=" + dir)
}
function toogleProtected(idx, b = 'false'){
	requestAPI("/api?type=command&param=setused&used=true&protected=" + b + "&idx=" + idx)
}

function refreshTemp(updateTemp) {
	$.each(updateTemp, function (i, idx) {
		var url = "/api?type=command&param=getdevices&rid=" + idx;
		requestAPI(url).then(jsonData => {
			var data = jsonData.result[0].Data;
			var temp = jsonData.result[0].Temp;
			var setpoint = jsonData.result[0].SetPoint
			var lastUpdate = jsonData.result[0].LastUpdate
			if (lastUpdate != null){ 
				$('#lastUpdate_' + idx).html(moment(lastUpdate).fromNow())
			}
			$('button[id="switch_' + idx + '"]').html(data)
			$('#data_'+ idx).html(data)
			$('#actual_data_'+ idx).html(temp)
			$('#tdata_'+ idx).html(data)
			$('#actual_tdata_'+ idx).html(temp)
			$('#range_'+ idx).val(setpoint)
			$('#slider_value_'+ idx).html(setpoint)
		});
	});
}

function refreshSwitches(updateSwitches) {
	$.each(updateSwitches, function (i, idx) {
		var url = "/api?type=command&param=getdevices&rid=" + idx;
		requestAPI(url).then(jsonData => {
			var data = jsonData.result[0].Data;
			var lastUpdate = jsonData.result[0].LastUpdate
			if (lastUpdate != null){
				$('#lastUpdate_' + idx).html(moment(lastUpdate).fromNow())
			};
			$('button[id="switch_' + idx + '"]').html(data);
			$('#data_' + idx).html(data);

			if (data == 'On'){
				if ($('#icon_OnOff_' + idx).html() == 'lightbulb'){
					$('#icon_OnOff_' + idx).css('color','#ffa700');
				}else{
					$('#icon_OnOff_' + idx).css('color', '#008744');
				}
				$('#icon_smoke_' + idx).html("detector_smoke").css('color','#ED2939');
				$('#data_smoke_'+ idx).html('Smoke detected!').css('color','#ED2939');
				$('#icon_MotionSensor_' + idx).html("motion_sensor_alert").css('color','#ED2939');
				$('#data_motion_' + idx).html('Motion detected!').css('color','#ED2939');
			}
			if (data == 'Open'){
				$('#icon_DoorContact_' + idx).html("door_open")
			}
			if (data == 'Unlocked'){
				$('#icon_DoorLock_' + idx).html("lock_open").css('color','#008000')
			}
			if (data == 'Off'){
				$('#icon_OnOff_' + idx).removeAttr('style')
				$('#icon_smoke_' + idx).html("detector").removeAttr('style')
				$('#data_smoke_'+ idx).html('No smoke').removeAttr('style')
				$('#icon_MotionSensor_' + idx).html("motion_sensor_idle").removeAttr('style')
				$('#data_motion_' + idx).html('Idle').removeAttr('style')
			}
			if (data == 'Closed'){
				$('#icon_DoorContact_' + idx).html("door_front")
			}
			if (data == 'Locked'){
				$('#icon_DoorLock_' + idx).html("lock").css('color','#ED2939')
			}
			if (data == 'Normal'){
				$('#icon_security_' + idx).removeAttr('style')
			}
			if (data == 'Arm Home'){
				$('#icon_security_' + idx).css('color','#ffa700')
			}
			if (data == 'Arm Away'){
				$('#icon_security_' + idx).css('color','#ffa700')
			}
		});		
	});
}

function refreshSelectors(updateSelector) {
	$.each(updateSelector, function (i, idx) {
		var url = "/api?type=command&param=getdevices&rid=" + idx;
		requestAPI(url).then(jsonData => {
			var level = jsonData.result[0].Level;
			var levelnames = jsonData['result'][0]['LevelNames'];
			var lastUpdate = jsonData.result[0].LastUpdate
			var offHidden = jsonData.result[0].LevelOffHidden
			if (lastUpdate != null){
				$('#lastUpdate_' + idx).html(moment(lastUpdate).fromNow())
			}
			btns = decodeBase64(levelnames).split('|');
			$.each(btns, function (i, lvlname) {
				if (i != '0') {
					i = i + '0';
				}
				if (level == i) {
					if ($('#Selector_' + idx + ' option[value="' + i + '"]').length == 0) {
						$('#Selector_' + idx).append('<option selected value="' + i +'">' + lvlname +'</option>')
					}
					if ($('#thermo_Selector_' + idx + ' option[value="' + i + '"]').length == 0) {
						$('#thermo_Selector_' + idx).append('<option selected value="' + i +'">' + lvlname +'</option>')
					}
					$('button[id="switch_' + idx + '"]').html(lvlname);
					$('#data_'+ idx).html(lvlname)
					$('#mode_data_'+ idx).html(lvlname)
					if (lvlname.toLowerCase() == 'off'){$('#thermo_icon_' + idx).html('thermostat').removeAttr('style')};
					if (lvlname.toLowerCase() == 'heat'){$('#thermo_icon_' + idx).html('mode_heat').css('color', '#ffa700')};
					if (lvlname.toLowerCase() == 'cool'){$('#thermo_icon_' + idx).html('mode_cool').css('color', '#2963FF')};
					if (lvlname.toLowerCase() == 'auto'){$('#thermo_icon_' + idx).html('thermostat_auto').removeAttr('style')};
					if (lvlname.toLowerCase() == 'eco'){$('#thermo_icon_' + idx).html('eco').css('color', '#008744')};
					if (lvlname.toLowerCase() == 'fan-only'){$('#thermo_icon_' + idx).html('mode_fan').removeAttr('style')};
					if (lvlname.toLowerCase() == 'purifier'){$('#thermo_icon_' + idx).html('air_purifier_gen').removeAttr('style')};
					if (lvlname.toLowerCase() == 'dry'){$('#thermo_icon_' + idx).html('cool_to_dry').removeAttr('style')};
					
				}else{
					if (offHidden == true && i != '0'){
						if ($('#Selector_' + idx + ' option[value="' + i + '"]').length == 0) {
							$('#Selector_' + idx).append('<option value="' + i +'">' + lvlname +'</option>')
						}
						if ($('#thermo_Selector_' + idx + ' option[value="' + i + '"]').length == 0) {
						$('#thermo_Selector_' + idx).append('<option value="' + i +'">' + lvlname +'</option>')
						}
					}
				}
				
			});
	 
		});
	});
}

function refreshScenes(updateScenes) {
	$.each(updateScenes, function (i, idx) {
		var url = "/api?type=command&param=getscenes&rid=" + idx;
		requestAPI(url).then(jsonData => {
			var data = jsonData.result[0].Status;
			var lastUpdate = jsonData.result[0].LastUpdate
			if (lastUpdate != null){
				$('#lastUpdate_' + idx).html(moment(lastUpdate).fromNow())
			}
			$('button[id="switch_' + idx + '"]').html(data)
			if (data != 'Off'){
				$('#icon_Group_' + idx).removeClass("bi bi-toggle2-off")
				$('#icon_Group_' + idx).addClass("bi bi-toggle2-on").css('color', '#008744')
			}else{
				$('#icon_Group_' + idx).removeClass("bi bi-toggle2-on")
				$('#icon_Group_' + idx).addClass("bi bi-toggle2-off").removeAttr('style')
			}
	 
		});
	});
}

function refreshDimmers(updateDimmers) {
	$.each(updateDimmers, function (i, idx) {
		var url = "/api?type=command&param=getdevices&rid=" + idx;
		requestAPI(url).then(jsonData => {
			var level = jsonData.result[0].Level;
			var data = jsonData.result[0].Data;
			var lastUpdate = jsonData.result[0].LastUpdate
			if (lastUpdate != null){
				$('#lastUpdate_' + idx).html(moment(lastUpdate).fromNow())
			}

			if (jsonData.result[0].Type == 'Color Switch'){
				var color = JSON.parse(jsonData.result[0].Color)
				var color_decimal = color.r * 65536 + color.g * 256 + color.b
				var hexcolor = color_decimal.toString(16)
				$('#rgb_' + idx).val('#' + hexcolor)
			};
			$('button[id="switch_' + idx + '"]').html(level + '%')		
			if (data != 'Off'){
				$('#data_'+ idx).html(level + '%')
				$('#icon_Dimmer_' + idx).css('color','#ffa700')
				$('#icon_ColorSwitch_' + idx).css('color','#ffa700')
				$('#icon_ColorSwitch_' + idx).css('color','#' + hexcolor)
				$('#slider_' + idx).val(level)
				$('#output_' + idx).html(level + '%');
			}else{
				$('#data_'+ idx).html('Off')
				$('#icon_Dimmer_' + idx).removeAttr('style')
				$('#icon_ColorSwitch_' + idx).removeAttr('style')
				$('#output_' + idx).html('Off');
				$('#slider_' + idx).val('0')
			}
	 
		});
	});
}

function changeRGB(ridx, val) {
   var rgbcode_stripped = val.substring(1);
	requestAPI("/api?type=command&param=setcolbrightnessvalue&idx=" + ridx + "&hex=" + rgbcode_stripped);
}

function changeDimmers(idx, val) {
    $('#output_' + idx).html(val);
	requestAPI("/api?type=command&param=switchlight&idx=" + idx + "&switchcmd=Set%20Level&level=" + val)
}

function setSetpoint(idx, protect) {
	var val = $('#range_' + idx).val();
	requesturl = "/api?type=command&param=setsetpoint&idx=" + idx + "&setpoint=" + val
	if (protect == 'true'){
		var pin = $('#inputPin_'+idx).val();
		requesturl = requesturl + "&passcode=" + pin
	}
	requestAPI(requesturl)	
}

function setArmLevel(idx) {
	var val = $('#Security_' + idx).val();
	var pin = $('#inputPin_' + idx).val();
	requestAPI("/api?custom=setArmLevel&armLevel=" + val + "&seccode=" + pin)
}

function setSelectorLevel(div, idx, protect) {
	var val = $(div + idx).val();
	requesturl = "/api?type=command&param=switchlight&idx=" + idx + "&switchcmd=Set%20Level&level=" + val
	if (protect == 'true'){
		var pin = $('#inputPin_'+idx).val();
		requesturl = requesturl + "&passcode=" + pin
	}
	requestAPI(requesturl)
}

function getUser(user) {
	var url = "/api?type=command&param=getusers"
	requestAPI(url).then(jsonData => {
		var data = jsonData
		if (data.status == 'ERR' || data.status == null) {
			$('#domoticzAdmin').val('No')
		} else {
			$('#domoticzAdmin').val('Yes')
		}			
	});
}
function getDzVersion() {
	var url = "/api?type=command&param=getversion"
	requestAPI(url).then(jsonData => {
		var data = jsonData
		$('#dzga-version').html(dzga_version)
		$('#dz-version').html(data.version)
	});
}

function getDeviceLog(idx) {
	var url = '/api?type=command&param=getlightlog&idx=' + idx
	requestAPI(url).then(jsonData => {
		var data = jsonData
		var html = '<table class="table table-sm small">'
        html += '<thead><tr><th scope="col">Date</th><th scope="col">Data</th><th scope="col">User</th></tr></thead><tbody>'
		html += '<tr><th scope="row">' + data.result[0].Date + '</th>'
        html += '<td>' + data.result[0].Data + '</td>'
        html += '<td>' + data.result[0].User + '</td></tr>'
		html += '<tr><th scope="row">' + data.result[1].Date + '</th>'
        html += '<td>' + data.result[1].Data + '</td>'
        html += '<td>' + data.result[1].User + '</td></tr>'
		html += '<tr><th scope="row">' + data.result[2].Date + '</th>'
        html += '<td>' + data.result[2].Data + '</td>'
        html += '<td>' + data.result[2].User + '</td></tr>'
		html += '<tr><th scope="row">' + data.result[3].Date + '</th>'
        html += '<td>' + data.result[3].Data + '</td>'
        html += '<td>' + data.result[3].User + '</td></tr>'
		html += '<tr><th scope="row">' + data.result[4].Date + '</th>'
        html += '<td>' + data.result[4].Data + '</td>'
        html += '<td>' + data.result[4].User + '</td></tr>'
		html += '<tr><th scope="row">' + data.result[5].Date + '</th>'
        html += '<td>' + data.result[5].Data + '</td>'
        html += '<td>' + data.result[5].User + '</td></tr>'
		html += '</tbody></table>'

		$('#device_log_' + idx).html(html)
		console.log(data.result[0])
	});	
}

function showDiv(that) {
    if (that.value == "true" && that.id == "ssl") {
        $("#pathcert").fadeIn(1000);
	$("#pathkey").fadeIn(1000);
    } else {
        $("#pathcert").fadeOut(500);
	$("#pathkey").fadeOut(500);
    }
    if (that.value == "nouser") {
        $(".forms").fadeOut(500);
    } else {
		$(".forms").hide();
        $("#passdiv_" + that.value).fadeIn(1000);
		$("#emaildiv_" + that.value).fadeIn(1000);
		$("#gassitdiv_" + that.value).fadeIn(1000);
		$("#submitdiv_" + that.value).fadeIn(1000);
		$("#admindiv_" + that.value).fadeIn(1000);
    }
	if (that.value == "newuser") {
        $(".newforms").fadeIn(1000);
	} else {
		$(".newforms").fadeOut(500);
	}
	if (that.value == "en") {
		$("#armhome_div").fadeOut(500);
		$("#armaway_div").fadeOut(500);

    } else {
        $("#armhome_div").fadeIn(1000);
		$("#armaway_div").fadeIn(1000);
    }
}

function checkVersion() {
  $.ajax({
    url: "https://raw.githubusercontent.com/DewGew/DZGA-Flask/development/VERSION.md",
    cache: false,
    success: function( data ) {
		dataFloat = data.split(",")[0];
    var compare = versionCompare(dataFloat, dzga_version);
    if (compare == 1) {
	  console.log(compare)
      $('#newver').html("<i>New version " + dataFloat + " is avalible, </i>");
	  $('#badge').show();
      $("#notes").html('You have 1 new notifications');
      $("#shownotes" ).show();
      }
    },
    async:true
    });
}
  
function versionCompare(a, b) {
    if (a === b) {
       return 0;
    }
    var a_components = a.split(".");
    var b_components = b.split(".");
    var len = Math.min(a_components.length, b_components.length);
    for (var i = 0; i < len; i++) {
        if (parseInt(a_components[i]) > parseInt(b_components[i])) {
            return 1;
        }
        if (parseInt(a_components[i]) < parseInt(b_components[i])) {
            return -1;
        }
    }
    if (a_components.length > b_components.length) {
        return 1;
    }
    if (a_components.length < b_components.length) {
        return -1;
    }
    return 0;
}

function decodeBase64(string) {
  characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";

  var result     = '';

  var i = 0;
  do {
      var b1 = characters.indexOf( string.charAt(i++) );
      var b2 = characters.indexOf( string.charAt(i++) );
      var b3 = characters.indexOf( string.charAt(i++) );
      var b4 = characters.indexOf( string.charAt(i++) );

      var a = ( ( b1 & 0x3F ) << 2 ) | ( ( b2 >> 4 ) & 0x3 );
      var b = ( ( b2 & 0xF  ) << 4 ) | ( ( b3 >> 2 ) & 0xF );
      var c = ( ( b3 & 0x3  ) << 6 ) | ( b4 & 0x3F );

      result += String.fromCharCode(a) + (b?String.fromCharCode(b):'') + (c?String.fromCharCode(c):'');

  } while( i < string.length );
return result;
}
