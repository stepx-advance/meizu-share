package local.pz261a.shareentry;

import android.app.PendingIntent;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.ContentObserver;
import android.net.wifi.WifiManager;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;
import android.widget.Toast;

public final class ShareTileService extends TileService {
    private boolean observing;
    private final ContentObserver observer = new ContentObserver(new Handler(Looper.getMainLooper())) {
        @Override public void onChange(boolean selfChange) { update(); }
    };

    @Override public void onStartListening() {
        super.onStartListening();
        if (!observing) {
            getContentResolver().registerContentObserver(Settings.Global.getUriFor(ShareController.KEY), false, observer);
            observing = true;
        }
        update();
    }
    @Override public void onStopListening() {
        if (observing) {
            getContentResolver().unregisterContentObserver(observer);
            observing = false;
        }
        super.onStopListening();
    }
    @Override public void onTileAdded() {
        super.onTileAdded();
        TileService.requestListeningState(this, new ComponentName(this, ShareTileService.class));
    }
    private void update() {
        Tile tile = getQsTile();
        if (tile == null) return;
        boolean enabled = ShareController.enabled(this);
        tile.setLabel("互传");
        tile.setSubtitle(enabled ? "已开启" : "已关闭");
        tile.setState(enabled ? Tile.STATE_ACTIVE : Tile.STATE_INACTIVE);
        tile.updateTile();
    }
    private void openSettings() {
        PendingIntent intent = PendingIntent.getActivity(this, 0,
                new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        startActivityAndCollapse(intent);
    }
    @Override public void onClick() {
        super.onClick();
        if (isLocked()) {
            unlockAndRun(new Runnable() {
                @Override public void run() { toggle(); }
            });
        } else {
            toggle();
        }
    }
    private void toggle() {
        try {
            if (checkSelfPermission("android.permission.WRITE_SECURE_SETTINGS") != PackageManager.PERMISSION_GRANTED) {
                openSettings();
                return;
            }
            boolean next = !ShareController.enabled(this);
            if (next) {
                WifiManager wifi = getSystemService(WifiManager.class);
                BluetoothManager manager = getSystemService(BluetoothManager.class);
                BluetoothAdapter bluetooth = manager == null ? null : manager.getAdapter();
                if (checkSelfPermission("android.permission.BLUETOOTH_CONNECT") != PackageManager.PERMISSION_GRANTED ||
                        wifi == null || !wifi.isWifiEnabled() || bluetooth == null || !bluetooth.isEnabled()) {
                    Toast.makeText(this, "请先打开蓝牙和 WLAN", Toast.LENGTH_LONG).show();
                    openSettings();
                    return;
                }
            }
            ShareController.setEnabled(this, next);
            update();
        } catch (RuntimeException error) {
            Toast.makeText(this, "请在互传设置中调整开关", Toast.LENGTH_LONG).show();
            openSettings();
        }
    }
}
