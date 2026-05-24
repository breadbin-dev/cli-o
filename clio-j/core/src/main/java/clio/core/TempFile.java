package clio.core;

import java.io.File;
import java.io.IOException;

public class TempFile implements Disposable {

    private final File file;

    public TempFile() {
        this("temp_", ".tmp");
    }

    public TempFile(String prefix, String suffix) {
        try {
            this.file = File.createTempFile(prefix, suffix);
            this.file.deleteOnExit();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public File file() {
        return this.file;
    }

    @Override
    public void close() {
        try {
            this.file.delete();
        }
        catch (Exception ex) {
            // pass
        }
    }
}

