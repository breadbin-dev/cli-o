package clio.router;

import clio.core.Dttms;
import java.time.LocalDateTime;
import java.util.*;

public class Publication {

    private final Map<String, Object> result = new TreeMap<>();

    private final Map<String, LocalDateTime> updatedDttm = new HashMap<>();
    private LocalDateTime lastUpdate;
    private LocalDateTime firstUpdate;

    private final String type;
    private final int refreshMs;

    public Publication(String type, int refreshMs) {
        this.type = type;
        this.refreshMs = refreshMs;
        this.lastUpdate = LocalDateTime.now();
        this.firstUpdate = lastUpdate;
    }

    public void update(Map<String, ?> updates, Boolean full) {
        synchronized (result) {
            lastUpdate = LocalDateTime.now();

            if (full != null && full) {
                result.clear();
                updatedDttm.clear();
                firstUpdate = lastUpdate;
            }
            result.putAll(updates);
            for (var k : updates.keySet())
                updatedDttm.put(k, lastUpdate);
        }
    }

    public Map<String, ?> results(LocalDateTime since, Map<String, Object> args) {
        synchronized (result) {
            var results = new HashMap<String, Object>();
            results.put("type", type);
            results.put("refresh_period", refreshMs);
            results.put("last_update", Dttms.formatDttm(lastUpdate));

            LinkedHashMap<String, Object> updates;
            if (since == null || since.isBefore(firstUpdate)) {
                updates = new LinkedHashMap<>(result);
                updates.put("__update_type__", "snapshot");
            } else {
                updates = new LinkedHashMap<>();
                for (var e : result.entrySet()) {
                    if (updatedDttm.get(e.getKey()).isAfter(since))
                        updates.put(e.getKey(), e.getValue());
                }
                updates.put("__update_type__", "delta");
            }

            if (args != null)
                filterResults(updates, args);

            results.put("result", updates);
            return results;
        }
    }

    private void filterResults(LinkedHashMap<String, Object> updates, Map<String, Object> args) {
        var ie = updates.entrySet().iterator();
        while(ie.hasNext()) {
            var row = ie.next();
            if (!row.getKey().startsWith("__")) {
                var obj = (Map<String, ?>) row.getValue();
                for (var ae : args.entrySet()) {
                    var av = obj.get(ae.getKey());
                    var arg = ae.getValue();
                    if (arg instanceof Set set) {
                        if (!set.contains(av))
                            ie.remove();
                    } else {
                        if (!arg.equals(av))
                            ie.remove();
                    }
                }
            }
        }
    }
}
