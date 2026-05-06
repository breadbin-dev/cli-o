package clio.core;

import org.slf4j.LoggerFactory;

public interface ErrorHandler {
    void onError(String key, String msg);

    default void onError(String key, Throwable ex) {
        this.onError(key, Exceptions.msg(ex));
    }

    default void safeOnError(String key, Throwable ex) {
        try {
            onError(key, ex);
        } catch (Throwable ex2) {
            var log = LoggerFactory.getLogger(Subscription.class);
            log.error("Problem handling err:", ex2);
            log.error("Original err:", ex);
        }
    }

    default void safeOnError(String key, String msg) {
        try {
            onError(key, msg);
        } catch (Throwable ex) {
            var log = LoggerFactory.getLogger(Subscription.class);
            log.error("Problem handling err:", ex);
            log.error("Original err: {}", msg);
        }
    }
}
