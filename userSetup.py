from maya import cmds
import shadeset

cmds.evalDeferred(shadeset.install, lowestPriority=True)
