function start_ttt(){
	QiSession(function(session){
		memraise(session,"Ulm/game","ttt");
	});
}

function start_vgw(){
	QiSession(function(session){
		memraise(session,"Ulm/game","vgw");
	});
}

function start_fm(){
	QiSession(function(session){
		memraise(session,"Ulm/game","fm");
	});
}

function start_hm(){
	QiSession(function(session){
		memraise(session,"Ulm/game","hm");
	});
}

function start_back(){
	QiSession(function(session){
		memraise(session,"Ulm/showMenu",1);
	});
}