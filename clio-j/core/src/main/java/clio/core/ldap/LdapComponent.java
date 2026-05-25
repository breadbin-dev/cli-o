package clio.core.ldap;

import clio.core.Application;
import clio.core.Component;
import clio.core.UserAuth;

public class LdapComponent implements Component {
    @Override
    public void start(Application app) {
        var url = app.ensureProperty("ldap_url");
        var username = app.ensureProperty("ldap_username");
        var password = app.ensureProperty("ldap_password");
        var searchBase = app.ensureProperty("ldap_searchbase");

        app.addService(new LdapUserAuth(url, username, password, searchBase), UserAuth.class);
    }

    @Override
    public void stop() {

    }
}
