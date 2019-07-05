class Color {

  static green() {
    return '#00AF41';
  }

  static orange() {
    return '#FF9933';
  }

  static red() {
    return '#EE6767';
  }

  static white() {
    return '#FFFFFF';
  }

  static yellow() {
    return '#FFFF66';
  }
}

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
      if (data['error']) {
        alert(data['error']);
        return;
      }

      // Update resources.
      $('#morningstar_analysis_pdf').attr('href', 'http://quotes.morningstar.com/stockq/analysis-report?&t=' + $ticker)

      // Update moat and management numbers.
      updateHtmlWithValueForKey(data, 'long_term_debt', true)
      updateHtmlWithValueForKey(data, 'free_cash_flow', true)
      var cash_flow = $('#free_cash_flow').html();
      if (parseInt(cash_flow) >= 0) {
        updateHtmlWithValueForKey(data, 'debt_payoff_time', false);
        colorCellWithIDForRange('#debt_payoff_time', [5, 4, 0]);
      } else {
        $('#debt_payoff_time').html('Negative Cash Flow');
        $('#debt_payoff_time').css('background-color', Color.red());
      }
      updateBigFiveHtmlWithDataForKey(data, 'eps');
      updateBigFiveHtmlWithDataForKey(data, 'sales');
      updateBigFiveHtmlWithDataForKey(data, 'equity');
      updateBigFiveHtmlWithDataForKey(data, 'roic');
      updateBigFiveHtmlWithDataForKey(data, 'cash');
    });
  });
});

function updateHtmlWithValueForKey(data, key, commas) {
  value = data[key];
  if (commas) {
    value = value.toLocaleString('en', {useGrouping:true});
  } else {
    value = value.toFixed(2);
  }
  $('#' + key).html(value);
}

function updateBigFiveHtmlWithDataForKey(data, key) {
  var row_data = data[key];
  var suffixes = ['_1_val', '_3_val', '_5_val', '_max_val'];
  for (var i = 0; i < suffixes.length; i++) {
    var element_id = '#' + key + suffixes[i];
    var value = '-';
    if (i < row_data.length) {
      value = row_data[i];
    }
    $(element_id).html(value);

    if (value == '-') {
      color = (i == 0) ? Color.red() :  Color.white()
      $(element_id).css('background-color', color);
    } else {
      colorCellWithIDForRange(element_id, [0, 5, 10]);
    }
  }
}

function colorCellWithIDForRange(id, range) {
    if (range.length != 3) {
      return;
    }
    value = $(id).html();
    var backgroundColor = Color.red();
    if (value >= range[2]) {
      backgroundColor = Color.green();
    } else if (value >= range[1]) {
      backgroundColor = Color.yellow();
    } else if (value >= range[0]) {
      backgroundColor = Color.orange();
    }
    $(id).css('background-color', backgroundColor);
}