bl_info = {
	"name": "Boo",
	"author": "Victor Jockin",
	"version": (0, 0, 4),
	"blender": (3, 6, 0),
	"location": "View3D > Object > Boo",
	"description": "",
	"warning": "In development / En cours de développement",
	"doc_url": "",
	"category": "",
}

from . import ui

def register() :
	ui.register()
	

def unregister() :
	ui.unregister()