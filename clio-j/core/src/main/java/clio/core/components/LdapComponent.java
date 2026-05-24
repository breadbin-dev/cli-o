package clio.core.components;

import clio.core.Application;
import clio.core.Component;
import clio.core.Ldap;
import clio.core.LdapAllowAll;

public class LdapComponent implements Component {
    @Override
    public void start(Application app) {
        if (app.isAuthDisabled()){
            app.addService(new LdapAllowAll(), Ldap.class);
        }
        else {
            var url = app.ensureProperty("ldap_url");
            var username = app.ensureProperty("ldap_username");
            var password = app.ensureProperty("ldap_password");
            var searchBase = app.ensureProperty("ldap_searchbase");

            app.addService(new Ldap(url, username, password, searchBase), Ldap.class);
        }
    }

    @Override
    public void stop() {

    }
}
