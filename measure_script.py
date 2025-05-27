import bpy
import sys
import os
import time

# --- Lire les arguments passés après "--"
argv = sys.argv
argv = argv[argv.index("--") + 1:]
model_path, email = argv[0], argv[1]

print(f"📥 Chargement modèle : {model_path}")
print(f"👤 Email utilisateur : {email}")

# --- Nettoyer la scène
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# --- Activer l'import .obj
bpy.ops.preferences.addon_enable(module="io_scene_obj")

# --- Importer le modèle
try:
    bpy.ops.import_scene.obj(filepath=model_path)
    print(" Modèle importé avec succès.")
except Exception as e:
    print(f" Échec import OBJ : {e}")
    sys.exit(1)

# --- Initialiser l’environnement boo_addon
try:
    from .addon import AddonStorage
    from .controllers import BooMainController

    AddonStorage.set("USER_EMAIL", email)
    controller = BooMainController()

    print(" Calibration en cours...")
    controller.doObjectCalibration()
    print(" Calibration terminée.")

    print(" Mesure en cours...")
    controller.doBreastMeasurement()
    print(" Mesure terminée.")

except Exception as e:
    print(f" Erreur pendant l’analyse : {e}")
    sys.exit(1)
