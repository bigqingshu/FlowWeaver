using System;
using System.Net;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class EngineHostApiClientTests
{
    [TestMethod]
    public async Task GetHealthAsyncDoesNotAttachAuthorization()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"status":"ok"},"error":null,"request_id":"health"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.GetHealthAsync(new EngineHostConnectionSettings
        {
            Token = "secret",
        });

        Assert.IsTrue(result.Ok);
        Assert.AreEqual("ok", result.Data?.Status);
        Assert.IsNull(handler.Authorization);
        Assert.AreEqual(new Uri("http://127.0.0.1:8000/api/v1/health"), handler.RequestUri);
    }

    [TestMethod]
    public async Task ListWorkflowsAsyncAttachesBearerToken()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListWorkflowsAsync(new EngineHostConnectionSettings
        {
            Token = "secret",
        });

        Assert.IsTrue(result.Ok);
        Assert.AreEqual("Bearer", handler.Authorization?.Scheme);
        Assert.AreEqual("secret", handler.Authorization?.Parameter);
        Assert.AreEqual(new Uri("http://127.0.0.1:8000/api/v1/workflows"), handler.RequestUri);
    }

    [TestMethod]
    public async Task ListWorkflowsAsyncRejectsMissingTokenBeforeRequest()
    {
        var handler = new StubHandler(_ => throw new InvalidOperationException("Should not send."));
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListWorkflowsAsync(new EngineHostConnectionSettings());

        Assert.IsFalse(result.Ok);
        Assert.AreEqual("TOKEN_REQUIRED", result.Error?.ErrorCode);
        Assert.AreEqual(0, handler.SendCount);
    }

    [TestMethod]
    public async Task ListEventsAsyncBuildsFilterQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListEventsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            afterSequenceNumber: 10,
            workflowRunId: "run-1",
            nodeRunId: "node-1",
            eventType: "NODE_TASK_PROGRESS",
            limit: 25);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/events?after_sequence_number=10&workflow_run_id=run-1&node_run_id=node-1&event_type=NODE_TASK_PROGRESS&limit=25"),
            handler.RequestUri);
    }

    [TestMethod]
    public async Task ListRunsAsyncBuildsWorkflowFilterQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListRunsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            workflowId: "wf-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs?workflow_id=wf-1"),
            handler.RequestUri);
    }

    [TestMethod]
    public async Task ListNodeRunsAsyncUsesRunPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListNodeRunsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run-1/nodes"),
            handler.RequestUri);
    }

    [TestMethod]
    public async Task CancelRunAsyncPostsToCancelPath()
    {
        HttpMethod? method = null;
        var handler = new StubHandler(request =>
        {
            method = request.Method;
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent("""{"ok":true,"data":{"process_id":"proc","workflow_run_id":"run-1","os_pid":null,"process_generation":1,"fencing_token":null,"status":"CANCEL_REQUESTED","started_at":"2026-06-29T01:02:03Z","last_heartbeat_at":null,"cancel_requested_at":"2026-06-29T01:03:03Z","exited_at":null,"exit_code":null,"error":null},"error":null,"request_id":"req"}"""),
            };
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.CancelRunAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Post, method);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run-1/cancel"),
            handler.RequestUri);
        Assert.AreEqual("CANCEL_REQUESTED", result.Data?.Status);
    }

    [TestMethod]
    public async Task ErrorEnvelopeIsReturned()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.Unauthorized)
        {
            Content = new StringContent("""{"ok":false,"data":null,"error":{"error_code":"UNAUTHORIZED","message":"Invalid local API token","details":{},"retryable":false},"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListWorkflowsAsync(new EngineHostConnectionSettings
        {
            Token = "bad",
        });

        Assert.IsFalse(result.Ok);
        Assert.AreEqual("UNAUTHORIZED", result.Error?.ErrorCode);
        Assert.AreEqual("Invalid local API token", result.Error?.Message);
        Assert.AreEqual("req", result.RequestId);
    }

    [TestMethod]
    public async Task InvalidBaseUrlIsReturnedAsErrorEnvelope()
    {
        var handler = new StubHandler(_ => throw new InvalidOperationException("Should not send."));
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListWorkflowsAsync(new EngineHostConnectionSettings
        {
            BaseUrl = "localhost:8000",
            Token = "secret",
        });

        Assert.IsFalse(result.Ok);
        Assert.AreEqual("INVALID_BASE_URL", result.Error?.ErrorCode);
        Assert.AreEqual(0, handler.SendCount);
    }

    [TestMethod]
    public async Task RequestFailureIsReturnedAsRetryableErrorEnvelope()
    {
        var handler = new StubHandler(_ => throw new HttpRequestException("connection refused"));
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListWorkflowsAsync(new EngineHostConnectionSettings
        {
            Token = "secret",
        });

        Assert.IsFalse(result.Ok);
        Assert.AreEqual("REQUEST_FAILED", result.Error?.ErrorCode);
        Assert.IsTrue(result.Error?.Retryable);
    }

    [TestMethod]
    public void RuntimeEventPayloadParses()
    {
        var runtimeEvent = EngineHostRuntimeEventStream.ParseRuntimeEvent(
            """{"event_id":"evt","sequence_number":7,"event_version":"1.0","event_type":"ENGINE_READY","timestamp":"2026-06-29T01:02:03Z","workflow_run_id":null,"node_run_id":null,"payload":{"status":"connected"}}""");

        Assert.AreEqual("evt", runtimeEvent.EventId);
        Assert.AreEqual(7, runtimeEvent.SequenceNumber);
        Assert.AreEqual("ENGINE_READY", runtimeEvent.EventType);
        Assert.AreEqual("connected", runtimeEvent.Payload.GetProperty("status").GetString());
    }

    [TestMethod]
    public void WorkflowRunDtoUsesActualJsonNames()
    {
        var envelope = JsonSerializer.Deserialize<ApiResponseEnvelope<WorkflowRunDto>>(
            """{"ok":true,"data":{"workflow_run_id":"run","workflow_id":"wf","revision_id":"rev","workflow_version":2,"definition_hash":"hash","status":"RUNNING","state_version":3,"owner_process_id":"proc","process_generation":1,"fencing_token":"fence","input_snapshot_id":null,"started_at":"2026-06-29T01:02:03Z","finished_at":null,"completion_reason":null,"error":null},"error":null,"request_id":"req"}""",
            FlowWeaverJson.Options);

        Assert.IsNotNull(envelope);
        Assert.IsTrue(envelope!.Ok);
        Assert.AreEqual("run", envelope.Data?.WorkflowRunId);
        Assert.AreEqual("RUNNING", envelope.Data?.Status);
        Assert.AreEqual(3, envelope.Data?.StateVersion);
    }

    private sealed class StubHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _send;

        public StubHandler(Func<HttpRequestMessage, HttpResponseMessage> send)
        {
            _send = send;
        }

        public Uri? RequestUri { get; private set; }

        public System.Net.Http.Headers.AuthenticationHeaderValue? Authorization { get; private set; }

        public int SendCount { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            SendCount++;
            RequestUri = request.RequestUri;
            Authorization = request.Headers.Authorization;
            return Task.FromResult(_send(request));
        }
    }
}
