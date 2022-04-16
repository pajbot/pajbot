'use strict';

$(window).on('load', function() {
    $('#toggle-module-checkbox').change(function() {
        let checked = this.checked;

        $.ajax({
            url: `/api/v1/modules/toggle/playsound`,
            type: 'POST',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify({
                new_state: checked,
            }),
            success: () => location.reload(),
        });
    });

    $('.volume-container').each(function(index, element) {
        let label = $('.volume-label', element);

        function updateLabel(newValue) {
            label.text(String(newValue));
        }

        let formElement = $('input', element.parentNode);

        function updateForm(newValue) {
            formElement.val(String(newValue));
        }

        let playerWrapper = $(element)
            .closest('tr')
            .find('.play-in-browser-wrapper');

        function updatePlayer(newValue) {
            playerWrapper.attr('data-volume', String(newValue));
        }

        let slider = $('.volume-slider', element);
        let start = parseInt(slider.attr('data-initial'));
        // init range library
        slider.range({
            min: 0,
            max: 100,
            start: start,
            step: 5,
            onChange: function(value, meta) {
                if (!meta.triggeredByUser) {
                    return;
                }

                updateLabel(value);
                updateForm(value);
                updatePlayer(value);
            },
        });
    });

    $('.link-input').on('input propertychange paste', function() {
        if (!this.value.match(/^https:\/\/\S*$/)) {
            this.setCustomValidity(
                'Playsound links must start with https:// and may not contain spaces'
            );
            return;
        } else {
            this.setCustomValidity('');
        }

        // update the link for the player
        let newValue = $(this).val();
        $(this)
            .closest('tr')
            .find('.play-in-browser-wrapper')
            .attr('data-link', newValue);
    });

    function getFormData(form) {
        let data = $(form)
            .serializeArray()
            .reduce((obj, item) => {
                obj[item.name] = item.value;

                if (item.name === 'volume' || item.name === 'cooldown') {
                    let val = parseInt(item.value);
                    if (isNaN(val)) {
                        val = null;
                    }
                    obj[item.name] = val;
                }
                return obj;
            }, {});

        // if the checkbox is checked, 'enabled' becomes 'on'
        // otherwise it's just not present (undefined)
        // so we make it a proper boolean here :-)
        data.enabled = 'enabled' in data;

        return data;
    }

    let messageBox = $('#message-box');
    let messageText = $('#message-text');

    $('#message-box-hide-icon').click(() => {
        messageBox.addClass('hidden');
    });

    function resultFeedback(success, text) {
        // reset state...
        messageBox.removeClass('hidden positive negative');

        // then update element.
        if (success) {
            messageBox.addClass('positive');
        } else {
            messageBox.addClass('negative');
        }
        messageText.text(text);
    }

    let createButton = $('#create-playsound-button');
    $('#new-playsound-form').submit(function(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const payload = {
            name: formData.get('name'),
            link: formData.get('link'),
        };
        console.log('New playsound');
        console.log(payload);

        $.ajax({
            url: `/api/v1/playsound/${encodeURIComponent(payload.name)}`,
            type: 'PUT',
            data: JSON.stringify(payload),
            contentType: 'application/json; charset=utf-8',
            headers: {
                'X-CSRFToken': csrf_token,
            },
            success: function(result) {
                console.log('success result', result);

                location.reload();
            },
            error: function(result) {
                console.log('error result', result);

                createButton.text('Create Playsound');
                createButton.removeClass('disabled');
                resultFeedback(false, 'Failed to create playsound');
            },
        });

        createButton.text('Creating Playsound...');
        createButton.addClass('disabled');
    });

    $('.playsound-form').each(function(index, form) {
        // formID is a string like form-doot for the "doot" playsound
        let formID = $(form).attr('id');

        // the DELETE button
        let deleteButton = $(
            `button.playsound-submit-delete[form=\"${formID}\"]`
        );
        deleteButton.click(function(event) {
            event.preventDefault();
            let formData = getFormData(form);
            // the formData.name comes from the hidden form input field with the playsound name
            console.log(`deleting playsound ${formData.name}`);
            console.log(formData);

            $('#delete-modal').modal('setting', {
                onApprove: () => {
                    $.ajax({
                        url: `/api/v1/playsound/${encodeURIComponent(
                            formData.name
                        )}`,
                        type: 'DELETE',
                        success: function(result) {
                            console.log('success result', result);

                            location.reload();
                        },
                        error: function(result) {
                            console.log('error result', result);

                            deleteButton.text('Delete');
                            deleteButton.removeClass('disabled');
                            resultFeedback(false, 'Failed to delete playsound');
                        },
                    });

                    deleteButton.text('Deleting...');
                    deleteButton.addClass('disabled');
                },
            });
            $('#delete-modal').modal('show');
        });

        let saveButton = $(`button.playsound-submit-save[form=\"${formID}\"]`);

        // the SAVE button
        function doSave(done, error) {
            if (!form.reportValidity()) {
                error();
                return;
            }

            let formData = getFormData(form);
            // the formData.name comes from the hidden form input field with the playsound name
            console.log(`updating playsound ${formData.name}`);
            console.log(formData);

            $.ajax({
                url: `/api/v1/playsound/${encodeURIComponent(formData.name)}`,
                type: 'POST',
                data: JSON.stringify(formData),
                contentType: 'application/json; charset=utf-8',
                headers: {
                    'X-CSRFToken': csrf_token,
                },
                success: function(result) {
                    console.log('success result', result);

                    saveButton.text('Save');
                    saveButton.removeClass('disabled');
                    resultFeedback(true, 'Successfully updated playsound');

                    if (done) {
                        done(result);
                    }
                },
                error: function(result) {
                    console.log('error result', result);

                    saveButton.text('Save');
                    saveButton.removeClass('disabled');
                    resultFeedback(false, 'Failed to update playsound');

                    if (error) {
                        error(result);
                    }
                },
            });

            saveButton.text('Saving...');
            saveButton.addClass('disabled');
        }

        $(form).submit(function(event) {
            event.preventDefault();
            doSave();
        });

        $(form)
            .closest('td')
            .find('.play-in-browser-wrapper')
            .each(function(index, wrapper) {
                let playButton = $(wrapper).find('.play-on-stream');

                $(playButton).click(() => {
                    let name = $(wrapper).attr('data-name');
                    let link = $(wrapper).attr('data-link');
                    let volume = parseInt($(wrapper).attr('data-volume'));

                    doSave(() => {
                        $.ajax({
                            url: `/api/v1/playsound/${encodeURIComponent(
                                name
                            )}/play`,
                            type: 'POST',
                        });
                    });
                });
            });
    });
});
