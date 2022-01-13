function click_ja(){
	QiSession(function(session){
		memread(session,"Ulm/ja_nein_context",function(context){
			memraise(session,"Ulm/ja_nein_antwort",context);
		});
	});
}

function click_nein(){
	QiSession(function(session){
		memraise(session,"Ulm/ja_nein_antwort","no");
	});
}

function click_nav(){
	QiSession(function(session){
		memraise(session,"Ulm/ja_nein_antwort","nav");
	});
}

function get_Question(){
	QiSession(function(session){
		memread(session,"Ulm/ja_nein_text",function(answer){
			$(".ja_nein_textbox").text(answer);
		});
	});
}

$( document ).ready(function() {
	get_Question();
});