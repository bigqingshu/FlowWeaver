using System;
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
}
