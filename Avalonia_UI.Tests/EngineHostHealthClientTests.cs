using System;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class EngineHostHealthClientTests
{
    [TestMethod]
    public async Task CheckAsyncReturnsHealthyForOkEnvelope()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"status":"ok"},"error":null,"request_id":"test"}"""),
        });
        var client = new EngineHostHealthClient(new HttpClient(handler));

        var result = await client.CheckAsync(new EngineHostConnectionSettings());

        Assert.IsTrue(result.IsHealthy);
        Assert.AreEqual("EngineHost health check passed.", result.Message);
        Assert.IsNull(result.ErrorMessage);
        Assert.AreEqual(new Uri("http://127.0.0.1:8000/api/v1/health"), handler.RequestUri);
    }

    [TestMethod]
    public async Task CheckAsyncReturnsErrorForHttpFailure()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.ServiceUnavailable)
        {
            ReasonPhrase = "Service Unavailable",
            Content = new StringContent("""{"ok":false,"data":null,"error":{"error_code":"UNAVAILABLE","message":"Service unavailable","details":{},"retryable":true},"request_id":"req"}"""),
        });
        var client = new EngineHostHealthClient(new HttpClient(handler));

        var result = await client.CheckAsync(new EngineHostConnectionSettings());

        Assert.IsFalse(result.IsHealthy);
        Assert.AreEqual("Connection failed.", result.Message);
        Assert.AreEqual("Service unavailable", result.ErrorMessage);
    }

    private sealed class StubHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _send;

        public StubHandler(Func<HttpRequestMessage, HttpResponseMessage> send)
        {
            _send = send;
        }

        public Uri? RequestUri { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            RequestUri = request.RequestUri;
            return Task.FromResult(_send(request));
        }
    }
}
