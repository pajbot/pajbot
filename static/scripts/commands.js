var key_labels = {
    sub_only: 'Only <strong>subscribers</strong> can use this command.',
    can_execute_with_whisper: `Can be executed by whispering <strong>${bot_name}</strong>`,
};

function handle_command(base_key, command) {
    $.each(command, function(key, value) {
        switch (key) {
            case 'resolve_string':
                var el = $(`div.sticky.${base_key} a.detailed`);

                if (value == null || value == false) {
                    el.hide();
                } else {
                    el.show();
                    var str;
                    if (command.id) {
                        str = `${command.id}-${value}`;
                    } else {
                        str = value;
                    }
                    el.attr('href', `/commands/${str}`);
                }
                break;

            case 'long_description':
                var el = $(`div.sticky.${base_key} div.long_description`);

                if (value == null || value == false) {
                    el.hide();
                } else {
                    el.show();
                    el.html(value);
                }
                break;

            case 'sub_only':
            case 'can_execute_with_whisper':
                var el = $(`div.sticky.${base_key} tr[data-key="${key}"]`);
                if (el.length == 0) {
                    return;
                }

                console.log(value);
                if (value == null || value == false) {
                    el.hide();
                } else {
                    el.show();
                    el.find('.value').html(key_labels[key]);
                }
                break;

            case 'cost':
                var el = $(`div.sticky.${base_key} tr[data-key="${key}"]`);
                if (el.length == 0) {
                    return;
                }

                console.log('Point cost is:', value);
                if (value == null || value == false) {
                    el.hide();
                } else {
                    el.show();
                    el.find('.value').html(value);
                }
                break;

            case 'examples':
                var el_base = $(`div.sticky.${base_key} .command-examples`);
                el_base.empty();
                if (value.length > 0) {
                    var $accordion = $('<div>', {
                        class: 'ui styled accordion examples',
                    });
                    el_base.append('<h5>Command examples</h5>');
                    el_base.append($accordion);
                    $.each(value, function(i, example) {
                        $accordion.append(
                            '<div class="title' +
                                (i == 0 ? ' active' : '') +
                                '"><i class="dropdown icon"></i> ' +
                                example.title +
                                '</div>'
                        );
                        var chat_html = '';
                        $.each(example.messages, function(i, message) {
                            chat_html += '<div class="chat border">';
                            chat_html +=
                                '<div class="chat-message ' +
                                message.source.type +
                                ' from-' +
                                message.source.from +
                                '">';
                            chat_html +=
                                '<span class="timestamp"><small>13:37</small></span>';
                            if (
                                message.source.type == 'say' ||
                                message.source.type == 'me'
                            ) {
                                /* BADGE START */
                                if (message.source.from == 'bot') {
                                    chat_html +=
                                        '<div class="pui badge bot"></div>&nbsp;';
                                } else if (
                                    command.level > 100 &&
                                    command.level < 420
                                ) {
                                    chat_html +=
                                        '<div class="pui badge turbo"></div>&nbsp;';
                                } else if (
                                    command.level >= 420 &&
                                    command.level < 500
                                ) {
                                    chat_html +=
                                        '<div class="pui badge helper"></div>&nbsp;';
                                } else if (
                                    command.mod_only ||
                                    (command.level >= 500 &&
                                        command.level < 750)
                                ) {
                                    chat_html +=
                                        '<div class="pui badge moderator"></div>&nbsp;';
                                } else if (
                                    command.level >= 750 &&
                                    command.level < 1000
                                ) {
                                    chat_html +=
                                        '<div class="pui badge globalmoderator"></div>&nbsp;';
                                } else if (
                                    command.level >= 1000 &&
                                    command.level < 2000
                                ) {
                                    chat_html +=
                                        '<div class="pui badge broadcaster"></div>&nbsp;';
                                } else if (command.level >= 2000) {
                                    chat_html +=
                                        '<div class="pui badge staff"></div>&nbsp;';
                                }
                                /* BADGE END */

                                chat_html +=
                                    '<span class="from ' +
                                    message.source.from +
                                    '">';
                                if (message.source.from == 'bot') {
                                    chat_html += bot_name;
                                } else {
                                    chat_html += 'pajlada';
                                }
                                chat_html += '</span>';
                            } else if (message.source.type == 'whisper') {
                                chat_html +=
                                    '<span class="from ' +
                                    message.source.from +
                                    '">';
                                if (message.source.from == 'bot') {
                                    chat_html += bot_name;
                                } else {
                                    chat_html += 'pajlada';
                                }
                                chat_html += '</span>';
                                chat_html +=
                                    '<svg class="svg"><polyline points="6 2, 10 6, 6 10, 6 2"></polyline></svg>';
                                chat_html +=
                                    '<span class="to ' +
                                    message.source.to +
                                    '">';
                                if (message.source.to == 'bot') {
                                    chat_html += bot_name;
                                } else {
                                    chat_html += 'pajlada';
                                }
                                chat_html += '</span>';
                            }
                            chat_html += '<span class="separator">:</span> ';
                            chat_html +=
                                '<span class="message autolink">' +
                                _.escape(message.message) +
                                '</span>';
                            chat_html += '</div>';
                            chat_html += '</div>';
                        });
                        $accordion.append(
                            '<div class="content' +
                                (i == 0 ? ' active' : '') +
                                '">' +
                                chat_html +
                                '</div>'
                        );
                    });
                    $accordion.accordion({
                        duration: 200,
                        collapsible: true,
                    });
                }
                break;

            default:
                var el = $(`div.sticky.${base_key} tr[data-key="${key}"]`);
                if (el.length == 0) {
                    return;
                }

                if (value == null) {
                    el.hide();
                } else {
                    el.show();
                    el.find('.value').text(value);
                }
                break;
        }
    });

    var segment = $(`div.sticky.${base_key} .supercool`);
    segment.removeClass('loading');

    refresh_sticky(base_key);
}

function refresh_sticky(base_key) {
    $(`.commandlist-container.${base_key}`).css(
        'min-height',
        $(`div.sticky.${base_key}`).height()
    );
    $(`.ui.sticky.${base_key}`).sticky('refresh');
}

$(document).ready(function() {
    $('table.command-data tr').hide();
    $('#commands .menu .item').tab({
        context: $('#commands'),
    });

    for (var i = 1; i <= 3; ++i) {
        $(`.ui.sticky.c${i}`).sticky({
            context: `.commandlist-container.c${i}`,
            offset: 67,
        });
    }

    function update_tab() {
        var hash = window.location.hash.substring(1);

        if (hash.length > 1) {
            var el = $(`#commands .menu .item.${hash}`);
            if (el !== undefined) {
                el.click();
            }
        }
    }

    update_tab();

    $(window).bind('hashchange', function(e) {
        update_tab();
    });

    $('table a.commandlink').api({
        action: 'commands',
        method: 'get',
        loadingDuration: 100,
        beforeSend: function(settings) {
            settings.urlData.raw_command_id = $(this).data('key');
            return settings;
        },
        onRequest: function(promise, xhr) {
            var base_key = $(this)
                .parent()
                .parent()
                .parent()
                .parent()
                .data('key');
            var help_segment = $(`div.sticky.${base_key} .help`);
            var segment = $(`div.sticky.${base_key} .supercool`);
            help_segment.hide();
            segment.show();
            segment.addClass('loading');
        },
        onComplete: function(response, element, xhr) {
            var base_key = $(this)
                .parent()
                .parent()
                .parent()
                .parent()
                .data('key');
            var segment = $(`div.sticky.${base_key} .supercool`);
            $(`table.${base_key} td.selectable`).removeClass('active');
            $(
                'table.' +
                    base_key +
                    ' td.selectable a.commandlink[data-key="' +
                    $(this).data('key') +
                    '"]'
            )
                .parent()
                .addClass('active');
            segment.removeClass('loading');
            refresh_sticky(base_key);
        },
        onSuccess: function(response, element, xhr) {
            var base_key = $(this)
                .parent()
                .parent()
                .parent()
                .parent()
                .data('key');
            handle_command(base_key, response.command);
            refresh_sticky(base_key);
        },
    });
});
