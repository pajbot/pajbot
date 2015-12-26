$(document).ready(function() {
    $('form').form({
        fields: {
            name: {
                identifier: 'name',
                rules: [
                {
                    type: 'empty',
                    prompt: 'You must enter a name for your Banphrase'
                }
                ]
            },
            length: {
                identifier: 'length',
                rules: [
                {
                    type: 'integer[1..1209600]',
                    prompt: 'Please enter a valid timeout duration in seconds (1-1209600)'
                }
                ]
            },
            phrase: {
                identifier: 'phrase',
                rules: [
                {
                    type: 'empty',
                    prompt: 'The banphrase cannot be empty'
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
