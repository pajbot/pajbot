$(document).ready(function() {
    $('form').form({
        fields: {
            name: {
                identifier: 'name',
                rules: [
                {
                    type: 'empty',
                    prompt: 'You must enter a name for your Timer'
                }
                ]
            },
            interval_online: {
                identifier: 'interval_online',
                rules: [
                {
                    type: 'integer[1..3600]',
                    prompt: 'Please enter a valid interval (1-3600)'
                }]
            },
            interval_offline: {
                identifier: 'interval_offline',
                rules: [
                {
                    type: 'integer[1..3600]',
                    prompt: 'Please enter a valid interval (1-3600)'
                }]
            },
            message: {
                identifier: 'message',
                rules: [
                {
                    type: 'empty',
                    prompt: 'The message cannot be empty'
                }
                ]
            },
        },
        keyboardShortcuts: false,
        onSuccess: function(event, fields) {
            console.log(fields);
        }
    });
});
