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

    const loader = document.querySelector("popup-loading");

    // Stop form from submitting normally.
    event.preventDefault();

    // Extract the URL path for the action.
    let $form = $(this);
    path = $form.attr('action');

    // Extract the ticker symbol.
    let $ticker = $('#ticker').val();
    if ($ticker.length == 0) {
      return;
    }

    // Start loading
    loader.show();

    // Post the data to the path.
    let posting = $.post(path, { ticker: $ticker } );

    posting.fail(function(response) {
    $.snackbar({
          content: `There was an error. Code ${response.status}`,
          style: 'toast',
          timeout: 3500
        });
        // Hide loading
        loader.hide();
        return;
    })
    // Update the HTML with the results.
    posting.done(function(json_data) {
      data = JSON.parse(json_data);
      if (data['error']) {
        $.snackbar({
          content: data['error'],
          style: 'toast',
          timeout: 3500
        });
        // Hide loading
        loader.hide();
        return;
      }

      // Update website title with the latest ticker symbol
      if (data.ticker) {
        let baseWebsiteTitle = document.title.split('?')[0] + '?';
        document.title = baseWebsiteTitle + ' - ' + data.ticker.toUpperCase();
      }
	  
	  // Update the "meaning" description
	  if (data.description) {
		$('#meaning').html(data.description);
	  }

      // Update moat numbers.
      updateBigFiveHtmlWithDataForKey(data, 'eps');
      updateBigFiveHtmlWithDataForKey(data, 'sales');
      updateBigFiveHtmlWithDataForKey(data, 'equity');
      updateBigFiveHtmlWithDataForKey(data, 'roic');
      updateBigFiveHtmlWithDataForKey(data, 'cash');

      // Update management numbers.
      updateHtmlWithValueForKey(data, 'debt_equity_ratio', /*commas=*/true);
      colorCellWithIDForZeroBasedRange('#debt_equity_ratio', [1, 2, 3]);
      updateHtmlWithValueForKey(data, 'total_debt', /*commas=*/true);
      updateHtmlWithValueForKey(data, 'free_cash_flow', /*commas=*/true);
      let cash_flow = $('#free_cash_flow').html();
      if (parseInt(cash_flow) >= 0) {
        updateHtmlWithValueForKey(data, 'debt_payoff_time', /*commas=*/false);
        colorCellWithIDForZeroBasedRange('#debt_payoff_time', [2, 3, 4]);
      } else {
        $('#debt_payoff_time').html('Negative Cash Flow');
        $('#debt_payoff_time').css('background-color', Color.red());
      }

      // Update margin of safety numbers
      updateHtmlWithValueForKey(data, 'margin_of_safety_price', /*commas=*/false);
      updateHtmlWithValueForKey(data, 'current_price', /*commas=*/false);
      updateHtmlWithValueForKey(data, 'sticker_price', /*commas=*/false);
      let marginOfSafety = data['margin_of_safety_price'];
      if (marginOfSafety) {
        let range = [marginOfSafety, marginOfSafety * 1.25, marginOfSafety * 1.5]
        colorCellWithIDForZeroBasedRange('#current_price', range);
      } else {
        colorCellWithBackgroundColor('#current_price', Color.red());
      }

      // Update Payback Time section
      let key = 'payback_time';
      updateHtmlWithValueForKey(data, key, /*commas=*/true);
      colorCellWithIDForZeroBasedRange('#' + key, [6, 8, 10]);
      if (!data[key]) {
        colorCellWithBackgroundColor('#' + key, Color.red());
      }

      // Update 10 Cap section
      let ten_cap_key = 'ten_cap_price';
      let ten_cap_field_id = '#' + ten_cap_key;
      let current_price = data['current_price'];
      updateHtmlWithValueForKey(data, ten_cap_key, /*commas=*/true);
      if (!data[ten_cap_key]) {
        colorCellWithBackgroundColor(ten_cap_field_id, Color.red());
      }
      if (current_price > data[ten_cap_key]) {
        colorCellWithBackgroundColor(ten_cap_field_id, Color.red());
      }
      else {
        colorCellWithBackgroundColor(ten_cap_field_id, Color.green());
      }


      // Update Market Cap numbers
      updateHtmlWithValueForKey(data, 'average_volume', /*commas=*/true);
      let averageVolume = data['average_volume'];
      let minVolume = data['current_price'] <= 1.0 ? 1000000 : 500000;
      let averageVolumeColor = averageVolume >= minVolume ? Color.green() : Color.red();
      colorCellWithBackgroundColor('#average_volume', averageVolumeColor);
      let sharesToHold = Math.round(averageVolume * 0.01).toLocaleString('en', {useGrouping:true});
      $('#shares_to_hold').html(sharesToHold);  // 1% of volume

      // Hide loading
      loader.hide();
    });
  });
});

function updateHtmlWithValueForKey(data, key, commas) {
  value = data[key];
  if (value === null) {
    $('#' + key).html('Undefined');
    return;
  }
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
      color = (i == 0) ? Color.red() :  Color.white();
      $(element_id).css('background-color', color);
    } else {
      colorCellWithIDForRange(element_id, [0, 5, 10], true);
    }
  }
}

function colorCellWithBackgroundColor(id, backgroundColor) {
    $(id).css('background-color', backgroundColor);
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
    colorCellWithBackgroundColor(id, backgroundColor);
}

function colorCellWithIDForZeroBasedRange(id, range) {
    if (range.length != 3) {
      return;
    }
    value = $(id).html();
    if (value == -1) {
      $(id).text('-');
      colorCellWithBackgroundColor(id, Color.white());
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

    colorCellWithBackgroundColor(id, backgroundColor);
}
