var focused = true;
var running = false;

$(document).ready(function() {
  // When the form  is clicked on, don't actually submit -- just send message.
  $('#form').submit(function() {
    $.post('ajax.html', { text: $('#text').val() });
    $('#text').val('');
    return false;
  });
  $('#text').focus(function() {
    if (this.value == "Type manual commands here...") {
      $(this).val("");
    }
  });

  // Send command when buttons are clicked on.
  $('td').click(function() {
    $.post('ajax.html', { text: $(this).attr('command') });
  });

  // Defer waitForUpdate so android browser thinks page is fully lodaed.
  setTimeout('waitForUpdate()', '10');

  $(window).blur(function() {
    focused = false;
  });
  $(window).focus(function() {
    focused = true;
    if (!running) waitForUpdate();
  });
});

function waitForUpdate() {
  if (focused == false) {
    running = false;
    return;
  }
  running = true;

  $.ajax({
    type: "GET",
    url: "ajax.html",
    async: true,
    cache: false,
    timeout: 60000,

    success: function(data) {
      $('#logmessages').text(data);
      waitForUpdate();
    },

    error: function(XMLHttpRequest, textStatus, errorThrown) {
      setTimeout('waitForUpdate()', '5000');
    },
  });
}
