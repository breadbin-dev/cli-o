package clio.core;

import javax.naming.AuthenticationException;
import javax.naming.Context;
import javax.naming.NamingException;
import javax.naming.directory.*;
import java.util.Hashtable;

public class Ldap {

    public record LdapUser(String username, String dn, String email) {};

    private final String url;
    private final String svcUser;
    private final String svcPwd;
    private final String searchBase;

    public Ldap(String url, String svcUser, String svcPwd, String searchBase) {
        this.url = url;
        this.svcUser = svcUser;
        this.svcPwd = svcPwd;
        this.searchBase = searchBase;
    }

    private Hashtable<String, String> env(String principle, String pwd) {
        var env = new Hashtable<String, String>();
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
        env.put(Context.PROVIDER_URL, url);
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        env.put(Context.SECURITY_PRINCIPAL, principle);
        env.put(Context.SECURITY_CREDENTIALS, pwd);
        return env;
    }

    public LdapUser lookupUser(String username) {
        try {
            var searchFilter = "sAMAccountname=" + username;

            var ctx = new InitialDirContext(env(svcUser, svcPwd));
            var searchControls = new SearchControls();
            searchControls.setSearchScope(SearchControls.SUBTREE_SCOPE);
            var results = ctx.search(searchBase, searchFilter, searchControls);

            if (results.hasMore()) {
                var result = results.next();
                var attrs = result.getAttributes();
                var email = attrs.get("mail").get().toString();
                var dn = result.getNameInNamespace();
                return new LdapUser(username, dn, email);
            }

            return null;
        }
        catch (Exception ex) {
            throw new RuntimeException("Problem looking up user [" + username + "]", ex);
        }
    }

    public boolean authUser(LdapUser user, String pwd) {
        try {
            new InitialDirContext(env(user.dn, pwd)).close();
            return true;
        } catch (AuthenticationException e) {
            return false;
        } catch (NamingException ex) {
            throw new RuntimeException("Problem authenticating up user [" + user.username + "]", ex);
        }
    }

    public LdapUser lookupAuthUser(String username, String password) {
        var user = lookupUser(username);
        if (user == null)
            throw new RuntimeException("User not found [" + username + "]");

        if (authUser(user, password))
            return user;

        throw new RuntimeException("Authentication failed [" + username + "]");
    }
}

