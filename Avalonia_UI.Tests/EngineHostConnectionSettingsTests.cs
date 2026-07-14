using System;
using System.Collections.Generic;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class EngineHostConnectionSettingsTests
{
    [TestMethod]
    public void BuildHealthUriUsesApiHealthPath()
    {
        var settings = new EngineHostConnectionSettings
        {
            BaseUrl = "http://127.0.0.1:8010",
        };

        Assert.AreEqual(
            new Uri("http://127.0.0.1:8010/api/v1/health"),
            settings.BuildHealthUri());
    }

    [TestMethod]
    public void BuildApiUriIncludesQueryAndEscaping()
    {
        var settings = new EngineHostConnectionSettings
        {
            BaseUrl = "http://127.0.0.1:8010/root",
        };

        var uri = settings.BuildApiUri(
            "/api/v1/events",
            new[]
            {
                new KeyValuePair<string, string?>("event_type", "NODE TASK"),
                new KeyValuePair<string, string?>("node_run_id", null),
                new KeyValuePair<string, string?>("limit", "10"),
            });

        Assert.AreEqual(
            new Uri("http://127.0.0.1:8010/api/v1/events?event_type=NODE%20TASK&limit=10"),
            uri);
    }

    [TestMethod]
    public void BuildRuntimeEventsWebSocketUriUsesTokenQuery()
    {
        var settings = new EngineHostConnectionSettings
        {
            BaseUrl = "https://engine.local:8443",
            Token = "secret token",
        };

        Assert.AreEqual(
            new Uri("wss://engine.local:8443/ws/v1/events?token=secret%20token"),
            settings.BuildRuntimeEventsWebSocketUri());
    }

    [TestMethod]
    public void BuildRuntimeEventsWebSocketUriRejectsMissingToken()
    {
        var settings = new EngineHostConnectionSettings();

        try
        {
            settings.BuildRuntimeEventsWebSocketUri();
            Assert.Fail("Expected an InvalidOperationException.");
        }
        catch (InvalidOperationException)
        {
        }
    }

    [TestMethod]
    public void BuildHealthUriRejectsRelativeUrl()
    {
        var settings = new EngineHostConnectionSettings
        {
            BaseUrl = "localhost:8000",
        };

        try
        {
            settings.BuildHealthUri();
            Assert.Fail("Expected an InvalidOperationException.");
        }
        catch (InvalidOperationException)
        {
        }
    }

    [TestMethod]
    public void BuildHealthUriRejectsNullBaseUrlWithoutThrowingNullReferenceException()
    {
        var settings = new EngineHostConnectionSettings
        {
            BaseUrl = null!,
        };

        try
        {
            settings.BuildHealthUri();
            Assert.Fail("Expected an InvalidOperationException.");
        }
        catch (InvalidOperationException exception)
        {
            Assert.AreEqual("EngineHost base URL is required.", exception.Message);
        }
    }

    [TestMethod]
    public void BuildRuntimeEventsWebSocketUriRejectsNullToken()
    {
        var settings = new EngineHostConnectionSettings
        {
            Token = null!,
        };

        try
        {
            settings.BuildRuntimeEventsWebSocketUri();
            Assert.Fail("Expected an InvalidOperationException.");
        }
        catch (InvalidOperationException exception)
        {
            Assert.AreEqual("EngineHost token is required.", exception.Message);
        }
    }
}
