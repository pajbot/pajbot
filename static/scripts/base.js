$.fn.api.settings.api = {
    'get_user': '/api/v1/user/{username}',
};

$(document).ready(function() {
    $('#usersearch').form({
        onSuccess: function(settings) {
            console.log('hi');
            console.log(settings);
            document.location.href = '/user/'+$('#usersearch input.username').val();
            return false;
        }
    });
});
