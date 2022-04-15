var paginate_data = {};

function paginate_refresh_buttons(key) {
    var data = paginate_data[key];

    var num_pages = Math.ceil(data.total / data.limit);
    var current_page =
        Math.round((data.offset / data.total) * (data.total / data.limit)) + 1;

    if (current_page == 1) {
        data['left_btn'].addClass('disabled');
    } else {
        data['left_btn'].removeClass('disabled');
    }

    if (current_page == num_pages) {
        data['right_btn'].addClass('disabled');
    } else {
        data['right_btn'].removeClass('disabled');
    }

    data['div_el'].find('a.page_btn').hide();

    if (data.show_ends === false) {
        var btn_index = 1;
        var num_buttons = 15;
        var max_buttons = 5;

        var btns = 0;

        data['div_el']
            .find('a.page_btn.icur')
            .text(current_page)
            .show();
        for (var i = 1; i < num_buttons; ++i) {
            var btn_id = Math.round(i / 2);
            var el = false;
            var id = 0;

            if (i % 2 == 0) {
                el = data['div_el'].find(`a.ib${7 - btn_id}`);
                id = current_page - btn_id;
            } else {
                el = data['div_el'].find(`a.ia${btn_id}`);
                id = current_page + btn_id;
            }

            if (id < 1 || id > num_pages) {
                continue;
            }

            if (btns > max_buttons) {
                break;
            }

            ++btns;

            el.data('id', id);
            el.text(id);
            el.show();
        }
    }
}

function paginate_add_rows(key, rows) {
    var data = paginate_data[key];
    data.body_el.append(rows);
}

function paginate_reload(key) {
    var el = $(key);
    var data = paginate_data[key];

    el.api({
        action: data.action,
        on: 'now',
        beforeSend: function(settings) {
            var key = $(this)
                .closest('.paginate_base')
                .data('paginate_key');
            var data = paginate_data[key];
            settings.data.offset = data.offset;
            settings.data.limit = data.limit;
            settings.data.direction = data.direction;
            return settings;
        },
        onSuccess: function(response, element, xhr) {
            paginate_on_success(response, element, xhr);

            var data = paginate_data[element.data('paginate_key')];
            data['div_el'].css('visibility', 'visible');
        },
    });
}

function paginate_on_success(response, element, xhr) {
    var key = element.closest('.paginate_base').data('paginate_key');
    var data = paginate_data[key];
    data.total = response._total;

    /* Refresh content */

    data.body_el.empty();

    data.on_success(response, key);

    paginate_refresh_buttons(key);
}

function paginate(selector, limit, direction, action, on_success, show_ends) {
    if (show_ends !== true) {
        show_ends = false;
    }
    var el = $(selector);
    var paginate_el = el.find('tfoot .paginate');
    var body_el = el.find('tbody');
    el.data('paginate_key', selector);
    paginate_data[selector] = {};
    paginate_data[selector]['el'] = el;
    paginate_data[selector]['paginator_el'] = paginate_el;
    paginate_data[selector]['body_el'] = body_el;
    paginate_data[selector]['offset'] = 0;
    paginate_data[selector]['limit'] = limit;
    paginate_data[selector]['direction'] = direction;
    paginate_data[selector]['total'] = 1;
    paginate_data[selector]['show_ends'] = show_ends;
    paginate_data[selector]['on_success'] = on_success;
    paginate_data[selector]['action'] = action;

    var buttons = '';
    for (var i = 0; i <= 6; ++i) {
        buttons += `<a class="item page_btn num ib${i}">${i}</a>`;
    }
    buttons += '<a class="item page_btn icur active">XD</a>';
    for (var i = 0; i <= 6; ++i) {
        buttons += `<a class="item page_btn num ia${i}">${i}</a>`;
    }

    /* Create menu base */
    paginate_el.append(
        '<div class="ui right floated pagination menu"><a class="item nleft"><i class="left chevron icon"></i></a>' +
            buttons +
            '<a class="item nright"><i class="right chevron icon"></i></a></div>'
    );

    paginate_data[selector]['div_el'] = paginate_el.find('div.pagination');
    paginate_data[selector]['left_btn'] = paginate_el.find('a.nleft');
    paginate_data[selector]['right_btn'] = paginate_el.find('a.nright');
    paginate_el.find('a.page_btn.num').api({
        action: action,
        beforeSend: function(settings) {
            var data =
                paginate_data[
                    $(this)
                        .parent()
                        .parent()
                        .parent()
                        .parent()
                        .parent()
                        .data('paginate_key')
                ];
            data.offset = ($(this).data('id') - 1) * data.limit;
            settings.data.offset = data.offset;
            settings.data.limit = data.limit;
            settings.data.direction = data.direction;
            return settings;
        },
        onSuccess: paginate_on_success,
    });

    paginate_el.find('.nleft').api({
        action: action,
        beforeSend: function(settings) {
            var key = $(this)
                .closest('.paginate_base')
                .data('paginate_key');
            var data = paginate_data[key];
            data.offset -= data.limit;
            settings.data.offset = data.offset;
            settings.data.limit = data.limit;
            settings.data.direction = data.direction;
            return settings;
        },
        onSuccess: paginate_on_success,
    });

    paginate_el.find('.nright').api({
        action: action,
        beforeSend: function(settings) {
            var key = $(this)
                .closest('.paginate_base')
                .data('paginate_key');
            var data = paginate_data[key];
            data.offset += limit;
            settings.data.offset = data.offset;
            settings.data.limit = data.limit;
            settings.data.direction = data.direction;
            return settings;
        },
        onSuccess: paginate_on_success,
    });

    paginate_reload(selector);
}
