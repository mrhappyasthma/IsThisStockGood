class Color {

  static green() {
    return '#C3E6CB';
  }

  static orange() {
    return '#FFD8A8';
  }

  static red() {
    return '#ffbdc4';
  }

  static white() {
    return '#FFFFFF';
  }

  static yellow() {
    return '#FFF0B5';
  }
}

// Attach a submit handler to the form.
$(document).ready(function() {
  $("#searchboxform").submit(function(event) {
    // Stop form from submitting normally.
    event.preventDefault();

    // Reset all cells
    resetAllCells();

    // Extract the URL path for the action.
    let $form = $(this);
    path = $form.attr('action');

    // Extract the ticker symbol.
    let $ticker = $('#ticker').val();
    if ($ticker.length == 0) {
      return
    }

    // Post the data to the path.
    let posting = $.post(path, { ticker: $ticker } );

    // Update the HTML with the results.
    posting.done(function(json_data) {
      data = JSON.parse(json_data);
      if (data['error']) {
        $.snackbar({
          content: data['error'],
          style: 'toast',
          timeout: 3500
        });
        return;
      }

      // Update moat and management numbers.
      updateHtmlWithValueForKey(data, 'debt_equity_ratio', true)
      colorCellWithIDForZeroBasedRange('#debt_equity_ratio', [1, 2, 3]);
      updateHtmlWithValueForKey(data, 'long_term_debt', true)
      updateHtmlWithValueForKey(data, 'free_cash_flow', true)
      let cash_flow = $('#free_cash_flow').html();
      if (parseInt(cash_flow) >= 0) {
        updateHtmlWithValueForKey(data, 'debt_payoff_time', false);
        colorCellWithIDForZeroBasedRange('#debt_payoff_time', [2, 3, 4]);
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

function resetAllCells() {

}

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
  let row_data = data[key];
  let suffixes = ['_1_val', '_3_val', '_5_val', '_max_val'];
  for (let i = 0; i < suffixes.length; i++) {
    let element_id = '#' + key + suffixes[i];
    let value = '-';
    if (i < row_data.length) {
      value = row_data[i];
    }
    $(element_id).html(value);

    if (value == '-') {
      color = (i == 0) ? Color.red() :  Color.white()
      $(element_id).css('background-color', color);
    } else {
      colorCellWithIDForRange(element_id, [0, 5, 10], true);
    }
  }
}

function colorCellWithIDForRange(id, range) {
    if (range.length != 3) {
      return;
    }
    value = $(id).html();
    let backgroundColor = Color.red();
    if (value >= range[2]) {
      backgroundColor = Color.green();
    } else if (value >= range[1]) {
      backgroundColor = Color.yellow();
    } else if (value >= range[0]) {
      backgroundColor = Color.orange();
    }
    $(id).css('background-color', backgroundColor);
}

function colorCellWithIDForZeroBasedRange(id, range) {
    if (range.length != 3) {
      return;
    }
    value = $(id).html();
    if (value == -1) {
      $(id).text('-');
      $(id).css('background-color', Color.white());
      return;
    }

    let backgroundColor = Color.green();
    if (value >= range[2]) {
      backgroundColor = Color.red();
    } else if (value >= range[1]) {
      backgroundColor = Color.orange();
    } else if (value >= range[0]) {
      backgroundColor = Color.yellow();
    }

    $(id).css('background-color', backgroundColor);
}