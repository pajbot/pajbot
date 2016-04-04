function load_widget(data)
{
    for (k in data) {
        var row = $('tr[data-key=\'' + k + '\']');
        load_value_into_row(row, k, data[k], 'default');
    }
}

function load_value_into_row(row, key, value, table_key)
{
    var text_input = row.find('input[type="text"]');
    if (text_input.length == 0) {
        text_input = row.find('textarea');
    }
    if (text_input.length == 1) {
        text_input.val(value);
    } else {
        var checkbox = row.find('input[type="checkbox"]');
        if (checkbox.length == 1) {
            checkbox[0].checked = value;
        } else {
            if (k == 'styles') {
                for (style in value) {
                    load_style(table_key, value[style]);
                }
            } else if (k == 'conditions') {
                for (condition in value) {
                    load_condition(value[condition]);
                }
            }
        }
    }
}

function load_condition(condition)
{
    var unique = add_condition();

    for (k in condition) {
        var row = $('table[data-condition="'+unique+'"] tr[data-key=\'' + k + '\']');
        load_value_into_row(row, k, condition[k], unique);
    }
}

function load_style(table_key, style)
{
    var unique = add_style(table_key);

    for (k in style) {
        var row = $('table[data-condition="'+table_key+'"] tbody[data-unique="'+unique+'"] tr[data-key=\'' + k + '\']');
        load_value_into_row(row, k, style[k], table_key);
    }
}

var unique_style_index = 0;
var unique_condition_index = 0;

function remove_current_style(unique)
{
    var el = $('tbody[data-unique="'+unique+'"]');
    var table_key = el.data('key');

    el.remove();

    recalculate_indices(table_key);
}

function remove_current_condition(unique)
{
    var el = $('table[data-condition="'+unique+'"]');

    el.remove();

    recalculate_conditions();
}

function add_new_style(unique)
{
    var table_key = $('.tbody[data-unique="'+unique+'"]').data('key');
    console.log('Adding NEW style to ' + table_key + ' (' + unique + ')');
    add_style(table_key);
}

function add_style(table_key)
{
    console.log('Adding style to ' + table_key);
    unique_style_index += 1;
    var $tbody = $('<tbody>', {'data-key': 'styles', 'data-unique': unique_style_index});

    {
        var $tr = $('<tr>');
        var $td = $('<td>', {colspan: 3}).html('<h4 class="style">Style #??</h4>');

        var $btn_add = $('<button>', {class: 'ui button btn_add', onclick: 'add_new_style("'+unique_style_index+'")'}).html('<i class="icon add green"></i> Add new style</button>');
        $td.append($btn_add);
        var $btn_remove = $('<button>', {class: 'ui button btn_remove', onclick: 'remove_current_style("'+unique_style_index+'")'}).html('<i class="icon remove red"></i> Remove this style</button>');
        $td.append($btn_remove);

        $tr.append($td);

        $tbody.append($tr);
    }

    {
        var $tr = $('<tr>', {'data-key': 'sound_url'});

        {
            var $td = $('<td>', {class: 'label'}).text('Sound URL');
            $tr.append($td);
        }
        {
            var $td = $('<td>');
            var $div = $('<div>', {class: 'ui input'});
            var $input = $('<input>', {type: 'text'});

            $div.append($input);
            $td.append($div);
            $tr.append($td);
        }

        $tr.append($td);
        $tbody.append($tr);
    }

    {
        var $tr = $('<tr>', {'data-key': 'sound_delay'});

        {
            var $td = $('<td>', {class: 'label'}).text('Sound Delay');
            $tr.append($td);
        }
        {
            var $td = $('<td>');
            var $div = $('<div>', {class: 'ui input'});
            var $input = $('<input>', {type: 'text', value: 0});

            $div.append($input);
            $td.append($div);
            $tr.append($td);
        }

        $tr.append($td);
        $tbody.append($tr);
    }

    {
        var $tr = $('<tr>', {'data-key': 'sound_volume'});

        {
            var $td = $('<td>', {class: 'label'}).text('Sound Volume');
            $tr.append($td);
        }
        {
            var $td = $('<td>');
            var $div = $('<div>', {class: 'ui input'});
            var $input = $('<input>', {type: 'text', value: 1.0});

            $div.append($input);
            $td.append($div);
            $tr.append($td);
        }

        $tr.append($td);
        $tbody.append($tr);
    }

    {
        var $tr = $('<tr>', {'data-key': 'image_url'});

        {
            var $td = $('<td>', {class: 'label'}).text('Image URL');
            $tr.append($td);
        }
        {
            var $td = $('<td>');
            var $div = $('<div>', {class: 'ui input'});
            var $input = $('<input>', {type: 'text'});

            $div.append($input);
            $td.append($div);
            $tr.append($td);
        }

        $tr.append($td);
        $tbody.append($tr);
    }

    $('table[data-condition="'+table_key+'"]').append($tbody);

    recalculate_indices(table_key);

    return unique_style_index;
}

function add_new_condition()
{
    var unique = add_condition();

    add_style(unique);
}

function add_condition()
{
    unique_condition_index += 1;

    var $table = $('<table>', {class: 'formtable ui single line table', 'data-condition': unique_condition_index});

    {
        var $thead = $('<thead>');
        {
            var $tr = $('<tr>');

            $tr.append($('<th>', {class: 'collapsing'}));
            $tr.append($('<th>'));
            $tr.append($('<th>', {class: 'collapsing'}));

            $thead.append($tr);
        }

        $table.append($thead);
    }

    {
        var $tbody = $('<tbody>', {'data-key': 'base'});

        {

        }

        $table.append($tbody);
    }

    {
        var $tr = $('<tr>');
        var $td = $('<td>', {colspan: 3}).html('<h4 class="condition">Condition #??</h4>');

        var $btn_add = $('<button>', {class: 'ui button btn_add', onclick: 'add_new_condition()'}).html('<i class="icon add green"></i> Add new condition</button>');
        $td.append($btn_add);
        var $btn_remove = $('<button>', {class: 'ui button btn_remove', onclick: 'remove_current_condition("'+unique_condition_index+'")'}).html('<i class="icon remove red"></i> Remove this condition</button>');
        $td.append($btn_remove);

        $tr.append($td);

        $tbody.append($tr);
    }

    {
        var $tr = $('<tr>', {'data-key': 'amount'});

        {
            var $td = $('<td>', {class: 'label'}).text('Amount');
            $tr.append($td);
        }
        {
            var $td = $('<td>');
            var $div = $('<div>', {class: 'ui input'});
            var $input = $('<input>', {type: 'text', value: 5});

            $div.append($input);
            $td.append($div);
            $tr.append($td);
        }

        $tr.append($td);
        $tbody.append($tr);
    }

    {
        var $tr = $('<tr>', {'data-key': 'operator'});

        {
            var $td = $('<td>', {class: 'label'}).text('Operator');
            $tr.append($td);
        }
        {
            var $td = $('<td>');
            var $select = $('<select>');
            {
                var $option = $('<option>').text('>=');
                $select.append($option);
            }
            {
                var $option = $('<option>').text('==');
                $select.append($option);
            }
            {
                var $option = $('<option>').text('<=');
                $select.append($option);
            }
            /*
            var $div = $('<div>', {class: 'ui input'});
            var $input = $('<input>', {type: 'text', value: '>='});

            $div.append($input);
            $td.append($div);
            */
            $td.append($select);
            $tr.append($td);
        }

        $tr.append($td);
        $tbody.append($tr);
    }

    $('#conditions').append($table);

    recalculate_conditions();

    return unique_condition_index;
}

function recalculate_indices(table_key)
{
    $.each($('table[data-condition="'+table_key+'"] tbody[data-key="styles"]'), function(index, el) {
        index += 1;
        $(el).data('index', index);
        $(el).find('h4.style').text('Style #'+index);

        var $btn_remove = $(el).find('button.btn_remove');

        if (index == 1) {
            $btn_remove.addClass('disabled');
        } else {
            $btn_remove.removeClass('disabled');
        }
    });
}

function recalculate_conditions()
{
    $.each($('#conditions table[data-condition!="default"]'), function(index, el) {
        index += 1;
        $(el).data('index', index);
        $(el).find('h4.condition').text('Condition #'+index);
    });
}

$(document).ready(function() {
    $('button.save').api({
        action: 'clr_donation_save',
        method: 'post',
        beforeSend: function(settings) {
            settings.urlData.widget_id = current_widget_id;
            var save_data = {
                'conditions': {},
                'styles': {},
            };

            $('tr').each(function() {
                var row = $(this);
                var key = row.data('key');
                if (key === undefined) {
                    return;
                }

                var tbody_key = row.parents('tbody').data('key');
                var table_condition = row.parents('table').data('condition');

                var value = null;
                var text_input = row.find('input[type="text"]');
                if (text_input.length == 0) {
                    text_input = row.find('textarea');
                }
                if (text_input.length == 1) {
                    value = text_input.val();
                } else {
                    var checkbox = row.find('input[type="checkbox"]');
                    if (checkbox.length == 1) {
                        value = checkbox[0].checked;
                    } else {
                        var select = row.find('select');
                        if (select.length == 1) {
                            value = select.val();
                        } else {
                            console.log(key);
                            console.error('BEEP BOOP');
                        }
                    }
                }
                var base = false;

                if (table_condition == 'default') {
                    base = save_data;
                } else {
                    if ((table_condition in save_data.conditions) == false) {
                        save_data.conditions[table_condition] = {
                            'styles': {}
                        };
                    }
                    base = save_data.conditions[table_condition];
                }

                if (tbody_key == 'base') {
                    base[key] = value;
                } else if (tbody_key == 'styles') {
                    var style_id = row.parents('tbody').data('unique');
                    if ((style_id in base.styles) == false) {
                        base.styles[style_id] = {};
                    }
                    base.styles[style_id][key] = value;
                } else {
                    console.error('WHY ' + tbody_key);
                    save_data[key] = value;
                }

            });

            function fix_styles(styles)
            {
                var real_styles = [];
                $.each(styles, function(index, val) {
                    real_styles.push(val);
                });
                return real_styles;
            }

            save_data.styles = fix_styles(save_data.styles);
            for (var i in save_data.conditions) {
                save_data.conditions[i].styles = fix_styles(save_data.conditions[i].styles);
            }
            save_data.conditions = fix_styles(save_data.conditions);

            save_data.styles = JSON.stringify(save_data.styles);
            save_data.conditions = JSON.stringify(save_data.conditions);

            settings.data = save_data;
            return settings;
        },
        onFailure: function(response) {
            console.error(response);
        }
    });
});
