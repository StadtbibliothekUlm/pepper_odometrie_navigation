function start_info_theke(){
	QiSession(function(session){
		memraise(session,"Ulm/start_info_theke","1");
	});
}

function start_info_bib(){
	QiSession(function(session){
		memraise(session,"Ulm/start_info_bib","1");
	});
}

function start_games(){
	QiSession(function(session){
		memraise(session,"Ulm/start_info_games","1");
	});
}

function start_say(){
	QiSession(function(session){
		ttssay(session,"Ich kann dir die Theke oder die Bibliothek der Dinge erklären oder du kannst mit mir spielen. Was möchtest du tun ?");
	});
}

$( document ).ready(function() {
	//start_say();
});