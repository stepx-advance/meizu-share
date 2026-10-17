package local.pz261a.shareentry;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.provider.Settings;

final class ShareController {
    static final String KEY = "meizu_share_provider";
    static boolean enabled(Context context) {
        return Settings.Global.getInt(context.getContentResolver(), KEY, 0) == 1;
    }
    static Intent settingsIntent() {
        return new Intent().setComponent(new ComponentName("com.meizu.share", "com.meizu.share.mutual.MutualSettingsActivity"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
    }
    static void setEnabled(Context context, boolean enabled) {
        if (enabled) {
            context.startForegroundService(new Intent().setComponent(
                    new ComponentName("com.meizu.share", "com.meizu.share.ShareService")));
        }
        if (!Settings.Global.putInt(context.getContentResolver(), KEY, enabled ? 1 : 0)) {
            throw new IllegalStateException("Could not update native share switch");
        }
    }
}
