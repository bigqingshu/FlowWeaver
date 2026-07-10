using System;
using System.Net;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
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
    public async Task ListNodeDefinitionsAsyncUsesReadOnlyPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[{"node_type":"GenerateTestTableNode","node_version":"1.0","display_name":"Generate Test Table","input_ports":[],"output_ports":[{"name":"out","required":false}],"input_table_slots":[{"name":"source","required":true,"allowed_storage_kinds":["RUNTIME_SQL","MEMORY"],"display_name":"Source","description":"Source table","default_source":"upstream_current"}],"output_table_slots":[{"name":"result","default_role":"CURRENT","allow_current":true,"allow_new_memory":true,"allow_new_runtime_sql":true,"allow_existing_memory":false,"allow_existing_runtime_sql":true,"display_name":"Result","description":"Result table"}],"execution_mode":"PROCESS_POOL","default_timeout_seconds":60,"retry_safe":false,"ui_visibility":"visible","config_schema_version":"1.0","config_schema":{"type":"object","properties":{"rows":{"type":"integer","title":"Rows","required":true,"default":3,"minimum":0}}}}],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListNodeDefinitionsAsync(new EngineHostConnectionSettings
        {
            Token = "secret",
        });

        Assert.IsTrue(result.Ok);
        Assert.AreEqual("Bearer", handler.Authorization?.Scheme);
        Assert.AreEqual(new Uri("http://127.0.0.1:8000/api/v1/node-definitions"), handler.RequestUri);
        Assert.AreEqual("GenerateTestTableNode", result.Data?[0].NodeType);
        Assert.AreEqual("out", result.Data?[0].OutputPorts[0].Name);
        Assert.AreEqual("source", result.Data?[0].InputTableSlots[0].Name);
        Assert.IsTrue(result.Data?[0].InputTableSlots[0].Required);
        CollectionAssert.AreEqual(
            new[] { "RUNTIME_SQL", "MEMORY" },
            result.Data?[0].InputTableSlots[0].AllowedStorageKinds);
        Assert.AreEqual("upstream_current", result.Data?[0].InputTableSlots[0].DefaultSource);
        Assert.AreEqual("result", result.Data?[0].OutputTableSlots[0].Name);
        Assert.IsTrue(result.Data?[0].OutputTableSlots[0].AllowNewRuntimeSql);
        Assert.IsTrue(result.Data?[0].OutputTableSlots[0].AllowExistingRuntimeSql);
        Assert.AreEqual("visible", result.Data?[0].UiVisibility);
        Assert.AreEqual("1.0", result.Data?[0].ConfigSchemaVersion);
        Assert.IsTrue(result.Data?[0].ConfigSchema.HasValue);
        var rowsSchema = result.Data![0]
            .ConfigSchema!.Value
            .GetProperty("properties")
            .GetProperty("rows");
        Assert.AreEqual("integer", rowsSchema.GetProperty("type").GetString());
        Assert.IsTrue(rowsSchema.GetProperty("required").GetBoolean());
    }

    [TestMethod]
    public async Task GetNodeDefinitionCatalogStateAsyncUsesStatePath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"catalog_hash":"hash-1","node_count":2,"program_hash":"build-1"},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.GetNodeDefinitionCatalogStateAsync(new EngineHostConnectionSettings
        {
            Token = "secret",
        });

        Assert.IsTrue(result.Ok);
        Assert.AreEqual("Bearer", handler.Authorization?.Scheme);
        Assert.AreEqual(new Uri("http://127.0.0.1:8000/api/v1/node-definitions/state"), handler.RequestUri);
        Assert.AreEqual("hash-1", result.Data?.CatalogHash);
        Assert.AreEqual(2, result.Data?.NodeCount);
        Assert.AreEqual("build-1", result.Data?.ProgramHash);
    }

    [TestMethod]
    public async Task GetWorkflowAsyncUsesDetailPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"workflow_id":"wf-1","name":"Flow","revision_id":"rev-1","version":2,"definition_hash":"hash-1","definition":{"schema_version":"1.0","nodes":[],"connections":[]},"status":"ACTIVE","created_at":"2026-06-29T01:02:03Z","updated_at":"2026-06-29T01:03:03Z"},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.GetWorkflowAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "wf 1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows/wf%201"),
            handler.RequestUri);
        Assert.AreEqual("wf-1", result.Data?.WorkflowId);
        Assert.AreEqual("rev-1", result.Data?.RevisionId);
        Assert.AreEqual("1.0", result.Data?.Definition.GetProperty("schema_version").GetString());
    }

    [TestMethod]
    public async Task DeleteWorkflowAsyncUsesDeletePath()
    {
        HttpMethod? method = null;
        var handler = new StubHandler(request =>
        {
            method = request.Method;
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent("""{"ok":true,"data":{"workflow_id":"wf-1","deleted":true},"error":null,"request_id":"req"}"""),
            };
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.DeleteWorkflowAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "wf 1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Delete, method);
        Assert.AreEqual("Bearer", handler.Authorization?.Scheme);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows/wf%201"),
            handler.RequestUri);
        Assert.AreEqual("wf-1", result.Data?.WorkflowId);
        Assert.IsTrue(result.Data?.Deleted);
    }

    [TestMethod]
    public async Task CreateWorkflowAsyncPostsCreatePayload()
    {
        HttpMethod? method = null;
        string? body = null;
        var handler = new StubHandler(request =>
        {
            method = request.Method;
            body = request.Content?.ReadAsStringAsync().GetAwaiter().GetResult();
            return new HttpResponseMessage(HttpStatusCode.Created)
            {
                Content = new StringContent("""{"ok":true,"data":{"workflow_id":"wf-1","name":"Created","revision_id":"rev-1","version":1,"definition_hash":"hash-1","definition":{"schema_version":"1.0","nodes":[],"connections":[]},"status":"ACTIVE","created_at":"2026-06-29T01:02:03Z","updated_at":"2026-06-29T01:03:03Z"},"error":null,"request_id":"req"}"""),
            };
        });
        var client = new EngineHostApiClient(new HttpClient(handler));
        using var definition = JsonDocument.Parse("""{"schema_version":"1.0","nodes":[],"connections":[]}""");

        var result = await client.CreateWorkflowAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "Created",
            definition.RootElement);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Post, method);
        Assert.AreEqual("Bearer", handler.Authorization?.Scheme);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows"),
            handler.RequestUri);
        Assert.IsNotNull(body);
        using var payload = JsonDocument.Parse(body!);
        Assert.AreEqual("Created", payload.RootElement.GetProperty("name").GetString());
        Assert.AreEqual(
            "1.0",
            payload.RootElement.GetProperty("definition").GetProperty("schema_version").GetString());
        Assert.AreEqual("wf-1", result.Data?.WorkflowId);
    }

    [TestMethod]
    public async Task ValidateWorkflowDraftAsyncPostsDraftPayload()
    {
        HttpMethod? method = null;
        string? body = null;
        var handler = new StubHandler(request =>
        {
            method = request.Method;
            body = request.Content?.ReadAsStringAsync().GetAwaiter().GetResult();
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent("""{"ok":true,"data":{"valid":false,"errors":[{"code":"UNKNOWN_NODE_TYPE","path":"nodes[0]","message":"Unknown node type/version: Missing@1.0"}],"warnings":[]},"error":null,"request_id":"req"}"""),
            };
        });
        var client = new EngineHostApiClient(new HttpClient(handler));
        using var definition = JsonDocument.Parse("""{"schema_version":"1.0","nodes":[],"connections":[]}""");

        var result = await client.ValidateWorkflowDraftAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            definition.RootElement);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Post, method);
        Assert.AreEqual("Bearer", handler.Authorization?.Scheme);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows/validate"),
            handler.RequestUri);
        Assert.IsNotNull(body);
        using var payload = JsonDocument.Parse(body!);
        Assert.AreEqual(
            "1.0",
            payload.RootElement.GetProperty("definition").GetProperty("schema_version").GetString());
        Assert.IsFalse(result.Data?.Valid);
        Assert.AreEqual("UNKNOWN_NODE_TYPE", result.Data?.Errors[0].Code);
    }

    [TestMethod]
    public async Task UpdateWorkflowAsyncPutsDraftWithBaseRevision()
    {
        HttpMethod? method = null;
        string? body = null;
        var handler = new StubHandler(request =>
        {
            method = request.Method;
            body = request.Content?.ReadAsStringAsync().GetAwaiter().GetResult();
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent("""{"ok":true,"data":{"workflow_id":"wf-1","name":"Updated","revision_id":"rev-2","version":2,"definition_hash":"hash-2","definition":{"schema_version":"1.0","nodes":[],"connections":[]},"status":"ACTIVE","created_at":"2026-06-29T01:02:03Z","updated_at":"2026-06-29T01:03:03Z"},"error":null,"request_id":"req"}"""),
            };
        });
        var client = new EngineHostApiClient(new HttpClient(handler));
        using var definition = JsonDocument.Parse("""{"schema_version":"1.0","nodes":[],"connections":[]}""");

        var result = await client.UpdateWorkflowAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "wf 1",
            "Updated",
            definition.RootElement,
            "rev-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Put, method);
        Assert.AreEqual("Bearer", handler.Authorization?.Scheme);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows/wf%201"),
            handler.RequestUri);
        Assert.IsNotNull(body);
        using var payload = JsonDocument.Parse(body!);
        Assert.AreEqual("Updated", payload.RootElement.GetProperty("name").GetString());
        Assert.AreEqual("rev-1", payload.RootElement.GetProperty("base_revision_id").GetString());
        Assert.AreEqual("rev-2", result.Data?.RevisionId);
    }

    [TestMethod]
    public async Task ListWorkflowRevisionsAsyncUsesRevisionsPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[{"revision_id":"rev-1","workflow_id":"wf-1","version":1,"definition_hash":"hash-1","definition":{"schema_version":"1.0"},"created_at":"2026-06-29T01:02:03Z","created_by":"tester"}],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListWorkflowRevisionsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "wf-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows/wf-1/revisions"),
            handler.RequestUri);
        Assert.AreEqual("rev-1", result.Data?[0].RevisionId);
        Assert.AreEqual("tester", result.Data?[0].CreatedBy);
    }

    [TestMethod]
    public async Task GetWorkflowRevisionAsyncUsesRevisionDetailPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"revision_id":"rev 1","workflow_id":"wf-1","version":1,"definition_hash":"hash-1","definition":{"schema_version":"1.0"},"created_at":"2026-06-29T01:02:03Z","created_by":null},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.GetWorkflowRevisionAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "wf-1",
            "rev 1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows/wf-1/revisions/rev%201"),
            handler.RequestUri);
        Assert.AreEqual("rev 1", result.Data?.RevisionId);
    }

    [TestMethod]
    public async Task StartWorkflowRunAsyncPostsPreviewTargetPayload()
    {
        HttpMethod? method = null;
        string? body = null;
        var handler = new StubHandler(request =>
        {
            method = request.Method;
            body = request.Content?.ReadAsStringAsync().GetAwaiter().GetResult();
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent("""{"ok":true,"data":{"workflow_run_id":"run-1","workflow_id":"wf-1","revision_id":"rev-1","workflow_version":2,"definition_hash":"hash","status":"PENDING","run_mode":"preview_to_node","target_node_instance_id":"node-1","state_version":1,"owner_process_id":null,"process_generation":0,"fencing_token":null,"input_snapshot_id":null,"started_at":null,"finished_at":null,"completion_reason":null,"error":null},"error":null,"request_id":"req"}"""),
            };
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.StartWorkflowRunAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "wf 1",
            "preview_to_node",
            "node-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Post, method);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows/wf%201/runs"),
            handler.RequestUri);
        Assert.IsNotNull(body);
        using var payload = JsonDocument.Parse(body!);
        Assert.AreEqual("preview_to_node", payload.RootElement.GetProperty("run_mode").GetString());
        Assert.AreEqual("node-1", payload.RootElement.GetProperty("target_node_instance_id").GetString());
        Assert.AreEqual("preview_to_node", result.Data?.RunMode);
        Assert.AreEqual("node-1", result.Data?.TargetNodeInstanceId);
    }

    [TestMethod]
    public async Task StartBackgroundWorkflowRunAsyncUsesBackgroundPathAndPayload()
    {
        string? body = null;
        var handler = new StubHandler(request =>
        {
            body = request.Content?.ReadAsStringAsync().GetAwaiter().GetResult();
            return new HttpResponseMessage(HttpStatusCode.Created)
            {
                Content = new StringContent("""{"ok":true,"data":{"workflow_run_id":"run-background","workflow_id":"wf-1","revision_id":"rev-1","workflow_version":2,"definition_hash":"hash","status":"PENDING","run_mode":"preview_to_node","trigger_source":"background_manual","target_node_instance_id":"node-1","state_version":1,"owner_process_id":null,"process_generation":0,"fencing_token":null,"input_snapshot_id":null,"started_at":null,"finished_at":null,"completion_reason":null,"error":null},"error":null,"request_id":"req"}"""),
            };
        });
        var service = new BackgroundRunService(
            new EngineHostApiClient(new HttpClient(handler)));

        var result = await service.StartAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "wf 1",
            "preview_to_node",
            "node-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Post, handler.RequestMethod);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/workflows/wf%201/background-runs"),
            handler.RequestUri);
        Assert.IsNotNull(body);
        using var payload = JsonDocument.Parse(body!);
        Assert.AreEqual("preview_to_node", payload.RootElement.GetProperty("run_mode").GetString());
        Assert.AreEqual("node-1", payload.RootElement.GetProperty("target_node_instance_id").GetString());
        Assert.AreEqual("background_manual", result.Data?.TriggerSource);
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
    public async Task ListRunsPageAsyncBuildsRuntimeFiltersAndPagination()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListRunsPageAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            workflowId: "wf 1",
            statuses: ["RUNNING", "SUCCEEDED"],
            runMode: "preview_to_node",
            triggerSource: "background_manual",
            offset: 20,
            limit: 40);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Get, handler.RequestMethod);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs?workflow_id=wf%201&status=RUNNING&status=SUCCEEDED&run_mode=preview_to_node&trigger_source=background_manual&offset=20&limit=40"),
            handler.RequestUri);
    }

    [TestMethod]
    public async Task RetryWorkflowRunAsyncPostsTriggerSource()
    {
        string? body = null;
        var handler = new StubHandler(request =>
        {
            body = request.Content?.ReadAsStringAsync().GetAwaiter().GetResult();
            return new HttpResponseMessage(HttpStatusCode.Created)
            {
                Content = new StringContent("""{"ok":true,"data":{"workflow_run_id":"run-retry","workflow_id":"wf-1","revision_id":"rev-1","workflow_version":2,"definition_hash":"hash","status":"PENDING","run_mode":"full","trigger_source":"background_manual","target_node_instance_id":null,"state_version":1,"owner_process_id":null,"process_generation":0,"fencing_token":null,"input_snapshot_id":null,"started_at":null,"finished_at":null,"completion_reason":null,"error":null},"error":null,"request_id":"req"}"""),
            };
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.RetryWorkflowRunAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run 1",
            "background_manual");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Post, handler.RequestMethod);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run%201/retry"),
            handler.RequestUri);
        Assert.IsNotNull(body);
        using var payload = JsonDocument.Parse(body!);
        Assert.AreEqual(
            "background_manual",
            payload.RootElement.GetProperty("trigger_source").GetString());
        Assert.AreEqual("run-retry", result.Data?.WorkflowRunId);
    }

    [TestMethod]
    public async Task CleanupRunTableRefsAsyncUsesDeleteAndParsesResult()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"workflow_run_id":"run-1","cleaned_count":1,"skipped_count":1,"failed_count":0,"cleaned_table_refs":[{"table_ref_id":"table-1","can_read_rows":false,"supports_paged_rows":false}],"skipped":[{"table_ref_id":"external-1","reason":"external_or_unsupported_storage"}],"failed":[]},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.CleanupRunTableRefsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run 1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Delete, handler.RequestMethod);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run%201/table-refs"),
            handler.RequestUri);
        Assert.AreEqual(1, result.Data?.CleanedCount);
        Assert.AreEqual("table-1", result.Data?.CleanedTableRefs[0].TableRefId);
        Assert.AreEqual("external-1", result.Data?.Skipped[0].TableRefId);
        Assert.AreEqual("external_or_unsupported_storage", result.Data?.Skipped[0].Reason);
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
    public async Task ListNodeRunsPageAsyncBuildsPagedFilterQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"items":[{"node_run_id":"node-run-1","workflow_run_id":"run-1","node_instance_id":"node-1","node_type":"FilterRowsNode","status":"RUNNING","state_version":2,"executor_id":null,"progress":0.5,"current_stage":"filter","attempt":1,"started_at":"2026-07-10T01:02:03Z","finished_at":null,"last_heartbeat":null,"error":null}],"offset":5,"limit":25,"total":6,"has_more":false},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListNodeRunsPageAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run 1",
            offset: 5,
            limit: 25,
            statuses: ["RUNNING", "PENDING"]);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run%201/nodes?paged=true&offset=5&limit=25&status=RUNNING&status=PENDING"),
            handler.RequestUri);
        Assert.AreEqual(6, result.Data?.Total);
        Assert.AreEqual("node-1", result.Data?.Items[0].NodeInstanceId);
        Assert.IsFalse(result.Data?.HasMore);
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
    public async Task ListTableRefsAsyncUsesRunPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListTableRefsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run-1/table-refs"),
            handler.RequestUri);
    }

    [TestMethod]
    public async Task ListRunTableDirectoryAsyncBuildsPagedFilterQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"items":[{"table_ref_id":"table-1","workflow_run_id":"run-1","node_run_id":"node-run-1","source_node_run_id":"node-run-1","source_node_instance_id":"node-1","role":"AUXILIARY","storage_kind":"RUNTIME_SQL","scope":"WORKFLOW_RUN","mutability":"IMMUTABLE","provider_id":"runtime-sql","resource_profile_id":"profile-1","mount_id":"mount-1","logical_table_id":"orders","output_slot":"result","table_type":"runtime_sql_table","preview_persistence":"workflow_run_sql","can_read_rows":true,"supports_paged_rows":true,"schema_fingerprint":"fp","version":2,"capabilities":["READ"],"lifecycle_status":"PUBLISHED","created_at":"2026-07-10T01:02:03Z"}],"offset":0,"limit":20,"total":1,"has_more":false},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListRunTableDirectoryAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run 1",
            limit: 20,
            nodeRunId: "node run 1",
            tableType: "runtime_sql_table",
            lifecycleStatuses: ["ACTIVE", "PUBLISHED"],
            logicalTableId: "daily orders");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run%201/table-refs?paged=true&offset=0&limit=20&node_run_id=node%20run%201&table_type=runtime_sql_table&lifecycle=ACTIVE&lifecycle=PUBLISHED&logical_table_id=daily%20orders"),
            handler.RequestUri);
        Assert.AreEqual(1, result.Data?.Total);
        Assert.AreEqual("node-1", result.Data?.Items[0].SourceNodeInstanceId);
        Assert.AreEqual("result", result.Data?.Items[0].OutputSlot);
        Assert.AreEqual("runtime_sql_table", result.Data?.Items[0].TableType);
        Assert.AreEqual("workflow_run_sql", result.Data?.Items[0].PreviewPersistence);
        Assert.IsTrue(result.Data?.Items[0].CanReadRows);
        Assert.IsTrue(result.Data?.Items[0].SupportsPagedRows);
        Assert.IsFalse(result.Data?.Items[0].Schema.HasValue);

        var item = new TableRefListItemViewModel(result.Data!.Items[0]);
        Assert.AreEqual("node-1", item.SourceNodeInstanceId);
        Assert.AreEqual("profile-1", item.ResourceProfileId);
        Assert.IsTrue(item.SupportsPagedRows);
    }

    [TestMethod]
    public async Task RunTableDirectoryServiceUsesOnlyPagedDirectoryQueries()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"items":[],"offset":0,"limit":10,"total":0,"has_more":false},"error":null,"request_id":"req"}"""),
        });
        var service = new RunTableDirectoryService(
            new EngineHostApiClient(new HttpClient(handler)));

        var nodeResult = await service.ListNodeRunsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run-1",
            limit: 10);

        Assert.IsTrue(nodeResult.Ok);
        Assert.AreEqual(1, handler.SendCount);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run-1/nodes?paged=true&offset=0&limit=10"),
            handler.RequestUri);

        var tableResult = await service.ListTableRefsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run-1",
            limit: 10);

        Assert.IsTrue(tableResult.Ok);
        Assert.AreEqual(2, handler.SendCount);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run-1/table-refs?paged=true&offset=0&limit=10"),
            handler.RequestUri);
    }

    [TestMethod]
    public async Task ListLoopRunsAsyncBuildsPagedStatusQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[{"loop_run_id":"loop-run-1","workflow_run_id":"run-1","loop_id":"orders-loop","start_node_instance_id":"start-1","judge_node_instance_id":"judge-1","status":"RUNNING","state_version":2,"current_iteration":1,"max_iterations":5,"exit_reason":null,"started_at":"2026-07-10T01:02:03Z","finished_at":null,"error":null,"created_at":"2026-07-10T01:01:03Z"}],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListLoopRunsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run 1",
            offset: 10,
            limit: 20,
            statuses: ["RUNNING", "COMPLETED"]);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Get, handler.RequestMethod);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run%201/loops?offset=10&limit=20&status=RUNNING&status=COMPLETED"),
            handler.RequestUri);
        Assert.AreEqual("orders-loop", result.Data?[0].LoopId);
        Assert.AreEqual(1, result.Data?[0].CurrentIteration);
        Assert.AreEqual(5, result.Data?[0].MaxIterations);
    }

    [TestMethod]
    public async Task ListLoopIterationsAsyncBuildsPagedStatusQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[{"loop_iteration_id":"iteration-1","loop_run_id":"loop-run-1","iteration_index":2,"status":"RUNNING","state_version":3,"input_table_ref_id":"input-1","input_selector":{"row_index":2},"output_table_ref_id":"output-1","failed_node_run_id":null,"started_at":"2026-07-10T01:02:03Z","finished_at":null,"error":null,"created_at":"2026-07-10T01:01:03Z"}],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListLoopIterationsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run 1",
            "loop run 1",
            offset: 5,
            limit: 15,
            statuses: ["RUNNING"]);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Get, handler.RequestMethod);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run%201/loops/loop%20run%201/iterations?offset=5&limit=15&status=RUNNING"),
            handler.RequestUri);
        Assert.AreEqual(2, result.Data?[0].IterationIndex);
        Assert.AreEqual(2, result.Data?[0].InputSelector?.GetProperty("row_index").GetInt32());
    }

    [TestMethod]
    public async Task ListLoopIterationNodeRunsAsyncUsesIterationNodesPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[{"loop_iteration_id":"iteration-1","node_run_id":"node-run-1","node_instance_id":"body-1","role":"BODY","node_type":"FilterRowsNode","status":"RUNNING","progress":0.5,"current_stage":"filter","attempt":1,"started_at":"2026-07-10T01:02:03Z","finished_at":null,"error":null}],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListLoopIterationNodeRunsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run 1",
            "loop run 1",
            "iteration 1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Get, handler.RequestMethod);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run%201/loops/loop%20run%201/iterations/iteration%201/nodes"),
            handler.RequestUri);
        Assert.AreEqual("BODY", result.Data?[0].Role);
        Assert.AreEqual("body-1", result.Data?[0].NodeInstanceId);
    }

    [TestMethod]
    public async Task ListLoopIterationTableRefsAsyncBuildsRoleQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[{"loop_iteration_id":"iteration-1","table_ref_id":"table-1","role":"OUTPUT","logical_table_id":"orders","storage_kind":"RUNTIME_SQL","table_role":"CURRENT","version":2,"lifecycle_status":"PUBLISHED","source_node_run_id":"node-run-1","source_node_instance_id":"body-1","output_slot":"result","created_at":"2026-07-10T01:02:03Z"}],"error":null,"request_id":"req"}"""),
        });
        var service = new LoopRunQueryService(
            new EngineHostApiClient(new HttpClient(handler)));

        var result = await service.ListIterationTableRefsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "run 1",
            "loop run 1",
            "iteration 1",
            role: "OUTPUT");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(HttpMethod.Get, handler.RequestMethod);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/runs/run%201/loops/loop%20run%201/iterations/iteration%201/table-refs?role=OUTPUT"),
            handler.RequestUri);
        Assert.AreEqual("OUTPUT", result.Data?[0].Role);
        Assert.AreEqual("body-1", result.Data?[0].SourceNodeInstanceId);
        Assert.AreEqual("result", result.Data?[0].OutputSlot);
    }

    [TestMethod]
    public async Task GetTableDataSchemaAsyncUsesDataSchemaPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"table_ref_id":"table-1","schema":[{"field_id":"f1","name":"row_id","data_type":"INTEGER","nullable":false,"ordinal":0}],"schema_fingerprint":"fp"},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.GetTableDataSchemaAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "table 1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/data/table%201/schema"),
            handler.RequestUri);
        Assert.AreEqual("table-1", result.Data?.TableRefId);
        Assert.AreEqual("row_id", result.Data?.Schema[0].Name);
        Assert.AreEqual("INTEGER", result.Data?.Schema[0].DataType);
    }

    [TestMethod]
    public async Task GetTableDataSummaryAsyncUsesDataSummaryPath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"table_ref_id":"table-1","workflow_run_id":"run-1","node_run_id":"node-run-1","logical_table_id":"orders","storage_kind":"RUNTIME_SQL","lifecycle_status":"PUBLISHED","version":2,"schema_fingerprint":"fp","capabilities":["READ"],"row_count":3},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.GetTableDataSummaryAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "table-1");

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/data/table-1/summary"),
            handler.RequestUri);
        Assert.AreEqual("orders", result.Data?.LogicalTableId);
        Assert.AreEqual(3, result.Data?.RowCount);
        CollectionAssert.AreEqual(new[] { "READ" }, result.Data?.Capabilities);
    }

    [TestMethod]
    public async Task GetTableDataRowsAsyncBuildsPreviewQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":{"table_ref_id":"table-1","offset":1,"limit":2,"row_count":3,"columns":["row_id","amount"],"rows":[{"row_id":2,"amount":3.0}],"has_more":false},"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.GetTableDataRowsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "table 1",
            offset: 1,
            limit: 2,
            columns: ["row_id", "amount"],
            orderBy: ["row_id"]);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/data/table%201/rows?offset=1&limit=2&columns=row_id&columns=amount&order_by=row_id"),
            handler.RequestUri);
        Assert.AreEqual(2, result.Data?.Columns.Length);
        Assert.AreEqual(2, result.Data?.Rows[0].GetProperty("row_id").GetInt32());
        Assert.AreEqual(3.0, result.Data?.Rows[0].GetProperty("amount").GetDouble());
    }

    [TestMethod]
    public async Task ListSharedPublicationsAsyncBuildsFilterQuery()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListSharedPublicationsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            shareName: "daily report",
            limit: 25);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/shared-publications?share_name=daily%20report&limit=25"),
            handler.RequestUri);
    }

    [TestMethod]
    public async Task ListSharedPublicationVersionsAsyncUsesSharePath()
    {
        var handler = new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("""{"ok":true,"data":[],"error":null,"request_id":"req"}"""),
        });
        var client = new EngineHostApiClient(new HttpClient(handler));

        var result = await client.ListSharedPublicationVersionsAsync(
            new EngineHostConnectionSettings { Token = "secret" },
            "daily report",
            limit: 10);

        Assert.IsTrue(result.Ok);
        Assert.AreEqual(
            new Uri("http://127.0.0.1:8000/api/v1/shared-publications/daily%20report/versions?limit=10"),
            handler.RequestUri);
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
            """{"ok":true,"data":{"workflow_run_id":"run","workflow_id":"wf","revision_id":"rev","workflow_version":2,"definition_hash":"hash","status":"RUNNING","run_mode":"preview_to_node","trigger_source":"background_manual","target_node_instance_id":"node-1","state_version":3,"owner_process_id":"proc","process_generation":1,"fencing_token":"fence","input_snapshot_id":null,"started_at":"2026-06-29T01:02:03Z","finished_at":null,"completion_reason":null,"error":null},"error":null,"request_id":"req"}""",
            FlowWeaverJson.Options);

        Assert.IsNotNull(envelope);
        Assert.IsTrue(envelope!.Ok);
        Assert.AreEqual("run", envelope.Data?.WorkflowRunId);
        Assert.AreEqual("RUNNING", envelope.Data?.Status);
        Assert.AreEqual("preview_to_node", envelope.Data?.RunMode);
        Assert.AreEqual("background_manual", envelope.Data?.TriggerSource);
        Assert.AreEqual("node-1", envelope.Data?.TargetNodeInstanceId);
        Assert.AreEqual(3, envelope.Data?.StateVersion);

        var item = new WorkflowRunListItemViewModel(envelope.Data!);
        Assert.AreEqual("background_manual", item.TriggerSource);
    }

    private sealed class StubHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _send;

        public StubHandler(Func<HttpRequestMessage, HttpResponseMessage> send)
        {
            _send = send;
        }

        public Uri? RequestUri { get; private set; }

        public HttpMethod? RequestMethod { get; private set; }

        public System.Net.Http.Headers.AuthenticationHeaderValue? Authorization { get; private set; }

        public int SendCount { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            SendCount++;
            RequestUri = request.RequestUri;
            RequestMethod = request.Method;
            Authorization = request.Headers.Authorization;
            return Task.FromResult(_send(request));
        }
    }
}
