using System;
using Avalonia_UI.Api;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class EngineHostConnectionDiagnosticsTests
{
    [TestMethod]
    public void DescribeErrorExplainsInvalidTokenAsWrongRotatedOrInvalid()
    {
        var response = ApiResponseEnvelope<string>.Failure(
            "UNAUTHORIZED",
            "Invalid local API token",
            requestId: "req");

        var description = EngineHostConnectionDiagnostics.DescribeError(response);

        Assert.AreEqual(
            "EngineHost token is wrong, rotated, or no longer valid. Re-enter the current local API token.",
            description);
    }

    [TestMethod]
    public void RedactTokenMasksRuntimeEventWebSocketUri()
    {
        var uri = new Uri(
            "ws://127.0.0.1:8000/ws/v1/events?token=super-secret&after_sequence_number=10");

        var redacted = EngineHostConnectionDiagnostics.RedactToken(uri);

        Assert.AreEqual(
            new Uri("ws://127.0.0.1:8000/ws/v1/events?token=***&after_sequence_number=10"),
            redacted);
        Assert.IsFalse(redacted.ToString().Contains("super-secret", StringComparison.Ordinal));
    }

    [TestMethod]
    public void DescribeRuntimeEventStreamExceptionRedactsToken()
    {
        var exception = new InvalidOperationException(
            "Could not connect ws://127.0.0.1:8000/ws/v1/events?token=super-secret");

        var description =
            EngineHostConnectionDiagnostics.DescribeRuntimeEventStreamException(exception);

        StringAssert.Contains(description, "RuntimeEvent stream connection failed");
        StringAssert.Contains(description, "token=***");
        Assert.IsFalse(description.Contains("super-secret", StringComparison.Ordinal));
    }
}
