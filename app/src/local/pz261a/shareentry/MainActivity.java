package local.pz261a.shareentry;

import android.app.Activity;
import android.os.Bundle;
import android.widget.Toast;

public final class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        try {
            startActivity(ShareController.settingsIntent());
        } catch (RuntimeException error) {
            Toast.makeText(this, "请先安装并启用魅族互传", Toast.LENGTH_LONG).show();
        }
        finish();
    }
}
