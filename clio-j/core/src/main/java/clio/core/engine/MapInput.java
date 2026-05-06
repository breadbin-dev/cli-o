package clio.core.engine;

import java.util.Map;

public interface MapInput<Tk, Tv, Tout> {

    void in(long seq, Tk key, Tv value);

    default void inAll(long seq, Map<Tk, Tv> in) {
        for (var i : in.entrySet())
            in(seq, i.getKey(), i.getValue());
    }

    Tout tick();
}
