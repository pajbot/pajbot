var changed_rows = [];
var invalid_rows = [];

function validate_value(row)
{
    var original_value = row.data('originalvalue');
    var value = row.data('value');
    var name = row.data('name');
    var type = row.data('type');

    var index = invalid_rows.indexOf(name);

    var parsed_value = value;

    switch (type) {
        case 'int':
            parsed_value = parseInt(parsed_value);
            if (isNaN(parsed_value)) {
                return false;
            }
            row.data('value', parsed_value);
            console.log(parsed_value);
            break;
        case 'string':
            if (parsed_value.length == 0) {
                return false;
            }
            break;
    }

    switch (name) {
        case 'level':
            break;
    }

    return true;
}

function update_row_text(row)
{
    var type = row.data('type');

    switch (type) {
        case 'boolean':
            row.find('div.display span.value').text(row.data('value') == 1 ? 'Yes' : 'No');
            break;

        default:
            row.find('div.display span.value').text(row.data('value'));
            break;
    }
}

function validate_row(row)
{
    update_row_text(row);

    if (validate_value(row) === false) {
        row.find('td.value').removeClass('warning');
        row.find('td.value').addClass('error');
        return false;
    }

    var original_value = row.data('originalvalue');
    var value = row.data('value');
    var name = row.data('name');

    var index = changed_rows.indexOf(name);

    update_row_text(row);

    if (row.data('originalvalue') == row.data('value')) {
        // Nothing was changed.
        row.find('td.value').removeClass('warning error');
        console.log('Nothing was changed');

        if (index !== -1) {
            changed_rows.splice(index, 1);
        }
    } else {
        row.find('td.value').removeClass('error');
        row.find('td.value').addClass('warning');
        console.log('value changed');

        if (index === -1) {
            changed_rows.push(name);
        }
    }

    if (changed_rows.length > 0 && invalid_rows.length == 0) {
        $('button.save-changes').removeClass('disabled');
    } else {
        $('button.save-changes').addClass('disabled');
    }
}

$(document).ready(function() {
    $('table.editcommand button.edit').click(function() {
        var row = $(this).parent().parent().parent();
        if (row.data('type') == 'boolean') {
            console.log(row.data('value'));
            x = row.data('value');
            row.find('div.edit input').prop('checked', row.data('value') == 1);
        } else {
            row.find('div.edit input').val(row.data('value'));
        }
        row.find('div.display').hide();
        row.find('div.edit').show();
    });

    $('table.editcommand button.cancel').click(function() {
        var row = $(this).parent().parent().parent();
        row.find('div.display').show();
        row.find('div.edit').hide();
    });

    $('table.editcommand button.save').click(function() {
        var row = $(this).parent().parent().parent();
        var new_value = row.find('div.edit input').val();
        var type = row.data('type');
        if (type == 'boolean') {
            var new_value = row.find('div.edit input').prop('checked');
            new_value = new_value == true ? 1 : 0;
        }
        row.data('value', new_value);
        validate_row(row);
        row.find('div.display').show();
        row.find('div.edit').hide();
    });

    $('table.editcommand .ui.dropdown').dropdown();

    $('table.editcommand .ui.checkbox').checkbox({
        onChange: function() {
            var label = $(this).parent().find('label');
            if ($(this).prop('checked')) {
                label.text('Yes');
            } else {
                label.text('No');
            }
        }
    });

    $('button.save-changes').api({
        action: 'edit_command',
        urlData: {
            'id': command_id,
        },
        method: 'post',
        beforeSend: function(settings) {
            if (invalid_rows.length > 0) {
                return false;
            }

            $.each(changed_rows, function(index, name) {
                var row = $('tr[data-name="'+name+'"]');
                var value = row.data('value');
                settings.data['data_' + name] = value;
                console.log(value);
            });

            return settings;
        },
        onSuccess: function(response, element, xhr) {
            $.each(changed_rows, function(index, name) {
                var row = $('tr[data-name="'+name+'"]');
                row.find('td.value').removeClass('warning');
                row.data('originalvalue', row.data('value'));
            });
            changed_rows = [];
            $('button.save-changes').addClass('disabled');
        }
    }).state({
        onActivate: function() {
            $(this).state('flash text');
        },
        text: {
            flash: 'Changes saved!'
        }
    });
});
