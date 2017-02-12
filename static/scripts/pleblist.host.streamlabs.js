var streamlabs_latest_donation_id = -1;

function streamlabs_get_donations(access_token)
{
    $.ajax({
        url: 'https://www.streamlabs.com/api/v1.0/donations?access_token=' + access_token + '&after=' + streamlabs_latest_donation_id,
        cache: false,
    }).done(function(result, b, c) {
        for (var i=result.data.length-1; i>=0; --i) {
            var donation = result.data[i];
            add_tip(donation.name, null, parseFloat(donation.amount) * 100, donation.message);
            streamlabs_latest_donation_id = parseInt(donation.donation_id);
        }
    });
}

function streamlabs_connect(access_token)
{
    console.log('TWITCHALERTS CONNECT');
    $.post('/api/v1/streamlabs/validate').done(function(data) {
        $('#notification').text('Successfully validated with TwitchAlerts');
        secret_password = data.password;
    }).fail(function(data) {
        $('#notification').text('Unable to validate with this TwitchAlerts. Contact pajlada if you believe this is wrong.');
    });

    streamlabs_get_donations(access_token);

    setInterval(function() {
        streamlabs_get_donations(access_token);
    }, 10 * 1000);
}
