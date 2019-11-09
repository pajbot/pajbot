(function () {
    moment.locale(window.navigator.language);

    function render_datetime(elem) {
        let ts = moment(parseFloat($(elem).data("timestamp")));
        let formatted = ts.format($(elem).data("format"));

        $(elem).text(formatted);
        $(elem).removeClass('localized-datetime');
    }

    function render_all_datetimes() {
        $('.localized-datetime').each(function () {
            render_datetime(this);
        })
    }

    $(document).ready(function () {
        render_all_datetimes();
    });
})();
