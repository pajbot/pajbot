'use strict';

$(document).ready(function () {
    let playButtons = $('.play-in-browser-play');
    let stopButtons = $('.play-in-browser-stop');


    $('.play-in-browser-wrapper').each(function (index, wrapper) {
        let playButton = $(wrapper).find('.play-in-browser-play');
        let stopButton = $(wrapper).find('.play-in-browser-stop');
        let player;

        $(playButton).click(() => {
            let link = $(wrapper).attr('data-link');
            let volume = parseInt($(wrapper).attr('data-volume'));

            let donePlaying = (e) => {
                if (e && typeof e !== 'number') {
                    console.warn(e);
                }

                playButtons.removeClass('disabled');
                playButtons.addClass('positive');

                stopButtons.removeClass('positive');
                stopButtons.addClass('disabled');
            };

            player = new Howl({
                src: [link],
                volume: volume * 0.01,  // the given volume is between 0 and 100
                onend: donePlaying,
                onstop: donePlaying,
                onloaderror: donePlaying,
                onplayerror: donePlaying
            });

            player.play();

            playButtons.removeClass('positive');
            playButtons.addClass('disabled');

            stopButton.removeClass('disabled');
            stopButton.addClass('positive');
        });

        $(stopButton).click(() => {
            player.stop();
        });

    });
});
