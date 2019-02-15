// Attach a submit handler to the form.
$(document).ready(function() {
  $("#searchboxform").submit(function(event) {
    // Stop form from submitting normally.
    event.preventDefault();

    // Extract the URL path for the action.
    var $form = $(this);
    path = $form.attr('action');

    // Extract the ticker symbol.
    var $ticker = $('#ticker').val();
    if ($ticker.length == 0) {
      return
    }

    // Post the data to the path.
    var posting = $.post(path, { ticker: $ticker } );

    // Update the HTML with the results.
    posting.done(function(json_data) {
      data = JSON.parse(json_data);
      updateHtmlWithDataForKey(data, 'eps');
      updateHtmlWithDataForKey(data, 'sales');
    });
  });
});

function updateHtmlWithDataForKey(data, key) {
  var row_data = data[key];
  var suffixes = ['_1_val', '_3_val', '_5_val', '_max_val'];
  for (var i = 0; i < row_data.length; i++) {
    var element_id = '#' + key + suffixes[i];
    var value = row_data[i]
    $(element_id).html(value);

    var backgroundColor = '#EE6767';
    if (value >= 10) {
      backgroundColor = '#00AF41';
    } else if (value >= 5) {
      backgroundColor = 'FFFF66';
    } else if (value >= 0) {
      backgroundColor = 'FF9933';
    }
    $(element_id).css('background-color', backgroundColor);
  }
}