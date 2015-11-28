function create_picker(selector, disabled_dates, highlight)
{
    $(selector).pickadate({
        disable: disabled_dates,
    });

    var picker = $(selector).pickadate('picker');
    if (picker === undefined) {
        return false;
    }
    picker.on({
        set: function(thing) {
            if (thing.select) {
                date_chosen = new Date(thing.select);
                var url = '/highlights/' + date_chosen.getFullYear() + '-' + (date_chosen.getMonth() + 1) + '-' + date_chosen.getDate() + '/';
                document.location.href = url;
            }
        },
    });
    if (highlight !== undefined) {
        picker.set('highlight', highlight);
    }
    picker.open(false);
}
