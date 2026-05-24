package clio.core;

import org.slf4j.Logger;

import java.util.function.BiConsumer;

public interface Subscription<T> extends ErrorHandler, Disposable {

    static <T> Subscription<T> withLog(BiConsumer<String, T> consumer, Logger log) {
        return withLog(consumer, log, false);
    }


    static <T> Subscription<T> withLog(BiConsumer<String, T> consumer, Logger log, boolean cleanLog) {
        return new Subscription<T>() {
            @Override
            public void accept(String key, T value) {
                consumer.accept(key, value);
            }

            @Override
            public void onError(String key, String msg) {
                if ("session".equals(key) && msg != null && msg.contains("NORMAL_CLOSURE")) {
                    log.info("[{}]: {}", key, Exceptions.cleanMessage(msg));
                } else {
                    if (cleanLog)
                        log.warn("[{}]: {}", key, Exceptions.cleanMessage(msg));
                    else
                        log.error("[{}]: {}", key, msg);
                }
            }
        };
    }

    void accept(String key, T value);

    default void safeAccept(String key, T value) {
        try {
            accept(key, value);
        } catch (Throwable ex) {
            safeOnError(key, ex);
        }
    }

    @Override
    default void close() {}

    default void safeClose() {
        try {
            close();
        } catch (Throwable ex) {
            safeOnError(null, ex);
        }
    }
}
