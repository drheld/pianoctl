$(document).ready(function() {
  $('#form').submit(function() {
    $.post('ajax.html', { text: $('#text').val() });
    $('#text').val('');
    return false;
  });

  $('td').click(function() {
    $.post('ajax.html', { text: $(this).attr('command') });
  });

  waitForUpdate();
});

function waitForUpdate() {
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
