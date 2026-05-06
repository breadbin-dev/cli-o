package clio.core;

import org.slf4j.Logger;

import java.util.List;

import static clio.core.Strings.f;

public interface Disposable extends AutoCloseable {
    static Disposable empty() {
        return () -> {};
    }

    @Override
    void close();

    default void safeClose(Logger log) {
        try {
            close();
        } catch (Throwable ex) {
            String desc = "Unknown";
            try {
                desc = this.toString();
            } catch (Throwable t) {
                // ignore
            }
            log.error(f("Problem closing [%s]", desc), ex);
        }
    }

    static void closeAll(List<Disposable> disposables, Logger log) {
        for (var disposable: disposables) {
            if (disposable != null)
                disposable.safeClose(log);
        }
    }
}
