function enable_edit_row(base) {
    $('button.edit-row').click(function() {
        var id = $(this)
            .parent()
            .parent()
            .data('id');
        document.location.href = '/admin/' + base + '/edit/' + id;
    });
}

function enable_remove_row(modal_class, action) {
    var id_remove = 0;
    $('button.remove-row').click(function() {
        id_remove = $(this)
            .parent()
            .parent()
            .data('id');
        $('.ui.modal.' + modal_class).modal('show');
    });
    $('.ui.modal.' + modal_class).modal({
        onApprove: function(el) {
            $.api({
                on: 'now',
                action: action,
                method: 'post',
                urlData: {
                    id: id_remove,
                },
                onSuccess: function(response, element) {
                    $('tr[data-id="' + id_remove + '"]').remove();
                },
                onFailure: function(response, element) {
                    console.error('something went wrong');
                },
                beforeXHR: function(xhr) {
                    xhr.setRequestHeader('X-CSRFToken', csrf_token);
                    return xhr;
                },
            });
        },
    });
}

function enable_toggle_row(action) {
    $('button.toggle-row').api({
        action: action,
        method: 'post',
        successTest: function(response) {
            return response.success || false;
        },
        beforeSend: function(settings) {
            var state = $(this)
                .parent()
                .parent()
                .data('enabled');
            console.log(state);
            settings.urlData.id = $(this)
                .parent()
                .parent()
                .data('id');
            if (state == '1') {
                settings.data.new_state = 0;
            } else {
                settings.data.new_state = 1;
            }
            return settings;
        },
        onSuccess: function(response, element) {
            $(this)
                .parent()
                .parent()
                .data('enabled', response.new_state);
            if (response.new_state == 1) {
                $(element)
                    .find('.text')
                    .text('Disable');
                $(element)
                    .find('.icon')
                    .removeClass('green')
                    .addClass('red');
            } else {
                $(element)
                    .find('.text')
                    .text('Enable');
                $(element)
                    .find('.icon')
                    .removeClass('red')
                    .addClass('green');
            }
        },
        beforeXHR: function(xhr) {
            xhr.setRequestHeader('X-CSRFToken', csrf_token);
            return xhr;
        },
    });
}

function enable_toggle_row_cb(action) {
    $('.toggle-row').api({
        on: 'change',
        action: action,
        method: 'post',
        successTest: function(response) {
            return response.success || false;
        },
        beforeSend: function(settings) {
            settings.contentType = 'application/json';
            const el = this[0];
            const state = el.checked;
            const module_id = el.dataset.id;
            settings.urlData.id = el.dataset.id;
            settings.data = JSON.stringify({ new_state: state });
            return settings;
        },
        onSuccess: function(response, element) {
            // const el = this[0];
            $(this)
                .parent()
                .parent()
                .parent()
                .data('enabled', response.new_state);
            if (response.new_state == 1) {
                $(element)
                    .find('.text')
                    .text('Disable');
                $(element)
                    .find('.icon')
                    .removeClass('green')
                    .addClass('red');
            } else {
                $(element)
                    .find('.text')
                    .text('Enable');
                $(element)
                    .find('.icon')
                    .removeClass('red')
                    .addClass('green');
            }
        },
        beforeXHR: function(xhr) {
            xhr.setRequestHeader('X-CSRFToken', csrf_token);
            return xhr;
        },
    });
}
