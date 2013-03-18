Array.prototype.remove = function(val) {
    for (var i = 0; i < this.length; i++) {
        if (this[i] === val) {
            this.splice(i, 1);
            i--;
        }
    }
    return this;
}

var app;

app = angular.module('tornado-demo',[]);


app.config(function ($interpolateProvider) {
    $interpolateProvider.startSymbol('[[');
    $interpolateProvider.endSymbol(']]');
});

function ContentCtrl($scope) {

    var host = "ws://127.0.0.1:8888/ws/";
    var ws = new WebSocket(host);

    $scope.reciever = '';

    $scope.users = [];
    $scope.messages = [];
    $scope.topics = [];

    $scope.new_topic = '';
    $scope.new_message = '';
    $scope.msg_sent = false;

    $scope.online = false;

    ws.onopen = function() {
        $scope.online=true;
        $scope.$apply();
    }

    ws.onclose = function() {
        $scope.online=false;
        $scope.$apply();
    }

    ws.onmessage = function(msg){

        console.log(msg);
        var data = JSON.parse(msg.data);

        switch (data.event) {
            case 'user_disconnected':
                // odhlaseni uzivatele
                $scope.users.remove(data.content.username);
                $scope.$apply();
                break;
            case 'user_connected':
                // novy uzivatel se pripojil
                $scope.users.push(data.content.username);
                $scope.$apply();
                break;
            case 'all_users':
                $scope.users = data.content.users;
                $scope.$apply();
                break;

            case 'all_topics':
                $scope.topics = data.content.topics;
                $scope.$apply();
                break;

            case 'new_topic':
                $scope.topics.unshift(data.content);
                $scope.$apply();
                break;

            case 'new_message':
                $scope.messages.unshift(data.content);
                $scope.$apply();
                break;


            case 'like':
                var top_id = data.content.topic_id;
                for(var i=0; i<$scope.topics.length; i++) {
                    if ($scope.topics[i]._id==top_id) {
                        $scope.topics[i].likes = data.content.likes;
                        break;
                    }
                }

                $scope.$apply();

        }
    };

    $scope.test = function() {
        $scope.users.push('test');
    }

    $scope.setReciever = function(r) {
        $scope.reciever = r;
        $scope.$apply();
    }

    $scope.add_topic = function(text) {
        ws.send(JSON.stringify({'event': 'new_topic', 'content': {'text': $scope.new_topic} }));
        $scope.new_topic = '';
    }

    $scope.like_topic = function(topic) {
        ws.send(JSON.stringify({'event': 'like', 'content': {'topic_id': topic._id} }));
    }

    $scope.sendMessage = function() {
        ws.send(JSON.stringify({'event': 'new_message', 'content': {'text': $scope.new_message, 'reciever': $scope.reciever } }));
        $scope.msg_sent = true;
        $scope.new_message = '';

    }

}