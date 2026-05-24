package clio.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.*;

public class SubscriptionFuture<T> implements Future<T> {

    private final List<Subscription<T>> listeners = new ArrayList<>();

    private T result;
    private boolean complete = false;
    private boolean cancelled = false;

    public void subscribe(Subscription<T> subscription) {
        Update<T> inline = null;
        synchronized (this) {
            if (unsafeIsDone())
                inline = new Update<>(Collections.singletonList(subscription), result, complete, cancelled);
            else
                listeners.add(subscription);
        }

        if (inline != null)
            inline.update();
    }

    // capture the update information within lock, in order to fire the event out of lock
    record Update<T>(List<Subscription<T>> subscriptions, T result, boolean complete, boolean cancelled) {
        void update() {
            if (complete) {
                for (var s : subscriptions)
                    s.safeAccept(null, result);
            }
            else if (cancelled) {
                for (var s : subscriptions)
                    s.safeOnError(null, "Cancelled");
            }
        }
    }

    private Update<T> takeListeners() {
        if (listeners.isEmpty())
            return null;

        var update = new Update<>(new ArrayList<>(listeners), result, complete, cancelled);
        listeners.clear();
        return update;
    }

    public void onResult(T result) {
        Update<T> inline;
        synchronized (this) {
            this.result = result;
            this.complete = true;
            inline = takeListeners();
            this.notifyAll();
        }

        if (inline != null)
            inline.update();
    }

    @Override
    public boolean cancel(boolean mayInterruptIfRunning) {
        Update<T> inline;
        var result = false;

        synchronized (this) {
            result = !unsafeIsDone();
            this.cancelled = true;
            inline = takeListeners();
            this.notifyAll();
        }

        if (inline != null)
            inline.update();

        return result;
    }

    @Override
    public boolean isCancelled() {
        synchronized (this) {
            return cancelled;
        }
    }

    private boolean unsafeIsDone() {
        return complete || cancelled;
    }

    @Override
    public boolean isDone() {
        synchronized (this) {
            return unsafeIsDone();
        }
    }

    @Override
    public T get() {
        return this.get(-1, null);
    }

    @Override
    public T get(long timeout, TimeUnit unit) {
        synchronized (this) {
            try {
                if (!unsafeIsDone()) {
                    if (timeout == -1)
                        this.wait();
                    else
                        this.wait(unit.toMillis(timeout));
                }
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            }
            if (cancelled)
                throw new CancellationException();

            return result;
        }
    }
}
