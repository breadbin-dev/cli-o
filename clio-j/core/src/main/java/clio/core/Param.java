package clio.core;

import org.apache.hc.client5.http.utils.Base64;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;

public record Param(String name, Object value) {

    public static Param basicAuth(String user, String password) {
        var creds = user + ":" + password;
        return new Param("Authorization", "Basic " + new String(Base64.encodeBase64(creds.getBytes(StandardCharsets.ISO_8859_1))));
    }

    public String toUrlParam() {
        String value;
        if (this.value() instanceof Iterable)
            value = String.join(",", (Iterable)this.value());
        else if (this.value() instanceof LocalDateTime)
            value = Dttms.formatISO((LocalDateTime)this.value());
        else
            value = this.value().toString();
        return this.name() + "=" + value;
    }
}
