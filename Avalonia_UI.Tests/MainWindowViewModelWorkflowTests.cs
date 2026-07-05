using System;
using System.Collections.Generic;
using System.Linq;
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
public sealed class MainWindowViewModelWorkflowTests
{
    [TestMethod]
    public async Task RefreshWorkflowsLoadsAndSelectsFirstWorkflow()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow("wf-1", "Daily Load", 1),
                    Workflow("wf-2", "Report", 2),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.HasCount(2, viewModel.Workflows);
        Assert.AreEqual("wf-1", viewModel.SelectedWorkflow?.WorkflowId);
        Assert.AreEqual("Loaded 2 workflow(s).", viewModel.WorkflowMessage);
        Assert.IsFalse(viewModel.HasWorkflowError);
        Assert.AreEqual("secret", apiClient.LastSettings?.Token);
    }

    [TestMethod]
    public async Task RefreshWorkflowsKeepsSelectionWhenStillPresent()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow("wf-1", "Daily Load", 1),
                    Workflow("wf-2", "Report", 2),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflow = viewModel.Workflows[1];
        apiClient.WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
            new List<WorkflowDefinitionDto>
            {
                Workflow("wf-2", "Report", 3),
                Workflow("wf-3", "Archive", 1),
            });

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-2", viewModel.SelectedWorkflow?.WorkflowId);
        Assert.AreEqual(3, viewModel.SelectedWorkflow?.Version);
    }

    [TestMethod]
    public async Task RefreshWorkflowsShowsErrorEnvelope()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Failure(
                "TOKEN_REQUIRED",
                "EngineHost token is required."),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.IsEmpty(viewModel.Workflows);
        Assert.AreEqual("Workflow refresh failed.", viewModel.WorkflowMessage);
        Assert.AreEqual("EngineHost token is required.", viewModel.WorkflowErrorMessage);
        Assert.IsTrue(viewModel.HasWorkflowError);
    }

    [TestMethod]
    public void HttpBusinessCommandsDoNotRequireRuntimeEventStreamConnection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.IsRuntimeEventStreamConnected);
        Assert.IsTrue(viewModel.CanUseEngineActions);
        Assert.IsTrue(viewModel.RefreshWorkflowsCommand.CanExecute(null));
        Assert.IsTrue(viewModel.CreateTemplateWorkflowCommand.CanExecute(null));
        Assert.IsTrue(viewModel.RefreshRunsCommand.CanExecute(null));

        viewModel.SelectedWorkflow = new WorkflowListItemViewModel(
            Workflow("wf-1", "Daily Load", 1));

        Assert.IsTrue(viewModel.StartSelectedWorkflowCommand.CanExecute(null));
        Assert.IsTrue(viewModel.LoadSelectedWorkflowDefinitionCommand.CanExecute(null));

        viewModel.SelectedRun = new WorkflowRunListItemViewModel(
            Run("run-1", "wf-1", "RUNNING"));

        Assert.IsTrue(viewModel.RefreshNodeRunsCommand.CanExecute(null));
        Assert.IsTrue(viewModel.CancelSelectedRunCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task BusinessCommandsAreDisabledAfterAuthenticationFailureUntilTokenChanges()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Failure(
                "UNAUTHORIZED",
                "Invalid local API token"),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.IsTrue(viewModel.IsAuthenticationFailed);
        Assert.IsFalse(viewModel.CanUseEngineActions);
        Assert.IsFalse(viewModel.RefreshWorkflowsCommand.CanExecute(null));
        Assert.IsFalse(viewModel.CreateTemplateWorkflowCommand.CanExecute(null));

        viewModel.Token = "new-secret";

        Assert.IsFalse(viewModel.IsAuthenticationFailed);
        Assert.IsTrue(viewModel.CanUseEngineActions);
        Assert.IsTrue(viewModel.RefreshWorkflowsCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task CreateTemplateWorkflowCreatesRefreshesAndSelectsCreatedWorkflow()
    {
        var createdWorkflow = Workflow(
            "wf-new",
            "Generated table workflow",
            1);
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { createdWorkflow }),
            CreateWorkflowResponse =
                ApiResponseEnvelope<WorkflowDefinitionDto>.Success(createdWorkflow),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.CreateTemplateWorkflowCommand.ExecuteAsync(null);

        Assert.AreEqual("Generated table workflow", apiClient.CreatedWorkflowName);
        Assert.IsNotNull(apiClient.CreatedWorkflowDefinition);
        var definition = apiClient.CreatedWorkflowDefinition.Value;
        Assert.AreEqual(
            "GenerateTestTableNode",
            definition.GetProperty("nodes")[0].GetProperty("node_type").GetString());
        Assert.AreEqual(
            "FilterRowsNode",
            definition.GetProperty("nodes")[1].GetProperty("node_type").GetString());
        Assert.AreEqual(
            "generate_to_filter",
            definition.GetProperty("connections")[0].GetProperty("connection_id").GetString());
        Assert.HasCount(1, viewModel.Workflows);
        Assert.AreEqual("wf-new", viewModel.SelectedWorkflow?.WorkflowId);
        Assert.AreEqual("Loaded 1 workflow(s).", viewModel.WorkflowMessage);
        Assert.IsFalse(viewModel.HasWorkflowError);
    }

    [TestMethod]
    public void CreateTemplateWorkflowIsDisabledForBlankName()
    {
        var viewModel = CreateViewModel(new FakeApiClient());
        viewModel.NewWorkflowName = "   ";

        Assert.IsFalse(viewModel.CreateTemplateWorkflowCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task CreateTemplateWorkflowShowsErrorEnvelope()
    {
        var apiClient = new FakeApiClient
        {
            CreateWorkflowResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "WORKFLOW_VALIDATION_FAILED",
                "Workflow definition is invalid."),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.CreateTemplateWorkflowCommand.ExecuteAsync(null);

        Assert.AreEqual("Workflow creation failed.", viewModel.WorkflowMessage);
        Assert.AreEqual(
            "WORKFLOW_VALIDATION_FAILED: Workflow definition is invalid.",
            viewModel.WorkflowErrorMessage);
        Assert.IsTrue(viewModel.HasWorkflowError);
        Assert.IsNull(viewModel.SelectedWorkflow);
    }

    [TestMethod]
    public async Task LoadSelectedWorkflowDefinitionLoadsDetailNodesConnectionsAndRevisions()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "display_name": "Source",
                  "config": {"rows": 3}
                },
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "enabled": false
                }
              ],
              "connections": [
                {
                  "connection_id": "c1",
                  "source_node_id": "source",
                  "source_port": "out",
                  "target_node_id": "filter",
                  "target_port": "in"
                }
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 2) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 2, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>
                {
                    Revision("rev-wf-1", "wf-1", 1, definitionJson),
                    Revision("rev-wf-1-2", "wf-1", 2, definitionJson),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", apiClient.LastWorkflowDetailId);
        Assert.AreEqual("wf-1", apiClient.LastWorkflowRevisionsWorkflowId);
        Assert.IsTrue(viewModel.HasWorkflowDefinition);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionError);
        var detail = viewModel.WorkflowDefinitionDetail;
        Assert.IsNotNull(detail);
        Assert.AreEqual("Daily Load", detail.Name);
        Assert.AreEqual("rev-wf-1", detail.RevisionId);
        Assert.AreEqual("hash-wf-1", detail.DefinitionHash);
        Assert.HasCount(2, detail.Nodes);
        Assert.HasCount(1, detail.Connections);
        Assert.HasCount(2, detail.Revisions);
        Assert.IsTrue(viewModel.HasWorkflowDefinitionDraftStructure);
        Assert.AreEqual(2, viewModel.WorkflowDefinitionDraftNodeCount);
        Assert.AreEqual("2 node(s)", viewModel.WorkflowDefinitionDraftNodeCountText);
        Assert.HasCount(2, viewModel.WorkflowDefinitionDraftNodes);
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftConnectionCount);
        Assert.IsNotNull(viewModel.WorkflowDefinitionDraftStructure);
        Assert.AreEqual(
            "source",
            viewModel.WorkflowDefinitionDraftStructure.Nodes[0].NodeInstanceId);
        Assert.AreEqual(
            "c1",
            viewModel.WorkflowDefinitionDraftStructure.Connections[0].ConnectionId);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionDraftStructureWarnings);
        Assert.AreSame(viewModel.WorkflowDefinitionDraftNodes[0], viewModel.SelectedWorkflowDefinitionNode);
        Assert.IsTrue(viewModel.HasSelectedWorkflowDefinitionNode);
        Assert.IsFalse(viewModel.HasNoSelectedWorkflowDefinitionNode);
        Assert.AreEqual("GenerateTestTableNode@1.0", detail.Nodes[0].TypeText);
        Assert.AreEqual(NodeEditorKind.JsonFallback, detail.Nodes[0].NodeEditorResolution.Kind);
        Assert.IsTrue(detail.Nodes[0].HasRegisteredNodeEditor);
        Assert.IsTrue(detail.Nodes[0].UsesJsonFallback);
        Assert.AreEqual(
            NodeEditorResolution.JsonFallbackStatusKey,
            detail.Nodes[0].NodeEditorResolution.StatusKey);
        Assert.AreEqual("JSON fallback", detail.Nodes[0].NodeEditorStatusText);
        Assert.AreEqual("disabled", detail.Nodes[1].EnabledText);
        Assert.AreEqual(
            "source.out -> filter.in",
            detail.Connections[0].EdgeText);
        StringAssert.Contains(
            detail.RawDefinitionJson,
            "\"schema_version\": \"1.0\"");
        Assert.AreEqual("Loaded Daily Load v2.", viewModel.WorkflowDefinitionMessage);
        StringAssert.Contains(viewModel.WorkflowDefinitionDraftJson, "\"schema_version\": \"1.0\"");
        Assert.IsTrue(viewModel.ValidateWorkflowDefinitionDraftCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task SelectingWorkflowFromLoadedListLoadsDefinitionAutomatically()
    {
        const string definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {}
                }
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow("wf-1", "Daily Load", 1),
                    Workflow("wf-2", "Report", 2),
                }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-2", "Report", 2, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflow = viewModel.Workflows[1];

        var autoLoadTask = viewModel.LoadSelectedWorkflowDefinitionCommand.ExecutionTask;
        Assert.IsNotNull(autoLoadTask);
        await autoLoadTask;

        Assert.AreEqual("wf-2", apiClient.LastWorkflowDetailId);
        Assert.AreEqual("wf-2", viewModel.WorkflowDefinitionDetail?.WorkflowId);
        Assert.AreEqual("Report", viewModel.WorkflowDefinitionDetail?.Name);
        Assert.IsTrue(viewModel.HasWorkflowDefinition);
        Assert.AreEqual("Loaded Report v2.", viewModel.WorkflowDefinitionMessage);
    }

    [TestMethod]
    public async Task ChangingWorkflowClearsPreviousNodeSelectionAndLoadsNewDefinition()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0"
                }
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow("wf-1", "Daily Load", 1),
                    Workflow("wf-2", "Other Flow", 1),
                }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsNotNull(viewModel.SelectedWorkflowDefinitionNode);

        apiClient.WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
            Workflow(
                "wf-2",
                "Other Flow",
                1,
                """{"schema_version":"1.0","nodes":[],"connections":[]}"""));
        viewModel.SelectedWorkflow = viewModel.Workflows[1];

        var autoLoadTask = viewModel.LoadSelectedWorkflowDefinitionCommand.ExecutionTask;
        Assert.IsNotNull(autoLoadTask);
        await autoLoadTask;

        Assert.AreEqual("wf-2", viewModel.WorkflowDefinitionDetail?.WorkflowId);
        Assert.IsNull(viewModel.SelectedWorkflowDefinitionNode);
        Assert.IsNull(viewModel.SelectedNodeConfigDraft);
        Assert.IsNull(viewModel.SelectedNodeConfigEditableDraft);
        Assert.IsFalse(viewModel.HasSelectedWorkflowDefinitionNode);
        Assert.IsTrue(viewModel.HasNoSelectedWorkflowDefinitionNode);
        Assert.IsFalse(viewModel.HasSelectedNodeConfigEditableInputFields);
        Assert.IsEmpty(viewModel.SelectedNodeConfigEditableInputFields);
        StringAssert.Contains(viewModel.WorkflowDefinitionDraftJson, "\"nodes\": []");
        Assert.IsNotNull(viewModel.WorkflowDefinitionDraftStructure);
        Assert.IsTrue(viewModel.HasWorkflowDefinitionDraftStructure);
        Assert.AreEqual(0, viewModel.WorkflowDefinitionDraftNodeCount);
        Assert.AreEqual(0, viewModel.WorkflowDefinitionDraftConnectionCount);
    }

    [TestMethod]
    public void WorkflowDefinitionDraftJsonChangesRefreshDraftStructureState()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        viewModel.WorkflowDefinitionDraftJson =
            """
            {
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0"}
              ],
              "connections": []
            }
            """;

        Assert.IsTrue(viewModel.HasWorkflowDefinitionDraftStructure);
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftNodeCount);
        Assert.AreEqual(0, viewModel.WorkflowDefinitionDraftConnectionCount);
        Assert.IsNotNull(viewModel.WorkflowDefinitionDraftStructure);
        Assert.AreEqual(
            WorkflowDefinitionDraftStructureStatus.Supported,
            viewModel.WorkflowDefinitionDraftStructure.Status);

        viewModel.WorkflowDefinitionDraftJson = """{"nodes":[]}""";

        Assert.IsFalse(viewModel.HasWorkflowDefinitionDraftStructure);
        Assert.IsTrue(viewModel.HasWorkflowDefinitionDraftStructureWarnings);
        Assert.AreEqual(0, viewModel.WorkflowDefinitionDraftNodeCount);
        Assert.AreEqual(0, viewModel.WorkflowDefinitionDraftConnectionCount);
        Assert.AreEqual(
            WorkflowDefinitionDraftStructureStatus.ConnectionsMissing,
            viewModel.WorkflowDefinitionDraftStructure?.Status);
    }

    [TestMethod]
    public async Task WorkflowDefinitionBatchSelectionTracksDraftNodeRefreshes()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "filter", "node_type": "FilterRowsNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual(0, viewModel.WorkflowDefinitionBatchSelectedNodeCount);
        Assert.AreEqual(
            "0 selected node(s)",
            viewModel.WorkflowDefinitionBatchSelectedNodeCountText);

        viewModel.WorkflowDefinitionDraftNodes.Single(node =>
            node.NodeInstanceId == "source").IsBatchSelected = true;
        viewModel.WorkflowDefinitionDraftNodes.Single(node =>
            node.NodeInstanceId == "filter").IsBatchSelected = true;

        Assert.AreEqual(2, viewModel.WorkflowDefinitionBatchSelectedNodeCount);
        Assert.AreEqual(
            "2 selected node(s)",
            viewModel.WorkflowDefinitionBatchSelectedNodeCountText);

        viewModel.WorkflowDefinitionDraftJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": []
            }
            """;

        Assert.AreEqual(1, viewModel.WorkflowDefinitionBatchSelectedNodeCount);
        Assert.IsTrue(viewModel.WorkflowDefinitionDraftNodes.Single(node =>
            node.NodeInstanceId == "source").IsBatchSelected);
        Assert.IsFalse(viewModel.WorkflowDefinitionDraftNodes.Single(node =>
            node.NodeInstanceId == "sink").IsBatchSelected);

        viewModel.WorkflowDefinitionDraftJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": []
            }
            """;

        Assert.AreEqual(0, viewModel.WorkflowDefinitionBatchSelectedNodeCount);
        Assert.AreEqual(
            "0 selected node(s)",
            viewModel.WorkflowDefinitionBatchSelectedNodeCountText);
    }

    [TestMethod]
    public async Task LoadingWorkflowDefinitionClearsDraftBatchSelection()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {}}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.WorkflowDefinitionDraftNodes.Single().IsBatchSelected = true;

        Assert.AreEqual(1, viewModel.WorkflowDefinitionBatchSelectedNodeCount);

        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual(0, viewModel.WorkflowDefinitionBatchSelectedNodeCount);
        Assert.IsFalse(viewModel.WorkflowDefinitionDraftNodes.Single().IsBatchSelected);
    }

    [TestMethod]
    public async Task DeleteSelectedWorkflowDefinitionDraftNodesCommandDeletesCheckedNodesAndConnections()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "filter", "node_type": "FilterRowsNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "join", "node_type": "FilterRowsNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"},
                {"connection_id": "filter_to_join", "source_node_id": "filter", "source_port": "out", "target_node_id": "join", "target_port": "in"},
                {"connection_id": "join_to_sink", "source_node_id": "join", "source_port": "out", "target_node_id": "sink", "target_port": "in"},
                {"connection_id": "keep", "source_node_id": "source", "source_port": "out", "target_node_id": "sink", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.DeleteSelectedWorkflowDefinitionDraftNodesCommand.CanExecute(null));

        viewModel.WorkflowDefinitionDraftNodes.Single(node =>
            node.NodeInstanceId == "filter").IsBatchSelected = true;
        viewModel.WorkflowDefinitionDraftNodes.Single(node =>
            node.NodeInstanceId == "join").IsBatchSelected = true;

        Assert.AreEqual(2, viewModel.WorkflowDefinitionBatchSelectedNodeCount);
        Assert.IsTrue(viewModel.DeleteSelectedWorkflowDefinitionDraftNodesCommand.CanExecute(null));

        viewModel.DeleteSelectedWorkflowDefinitionDraftNodesCommand.Execute(null);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        var nodes = draft.RootElement.GetProperty("nodes");
        Assert.AreEqual(2, nodes.GetArrayLength());
        Assert.AreEqual("source", nodes[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("sink", nodes[1].GetProperty("node_instance_id").GetString());

        var connections = draft.RootElement.GetProperty("connections");
        Assert.AreEqual(1, connections.GetArrayLength());
        Assert.AreEqual("keep", connections[0].GetProperty("connection_id").GetString());
        Assert.AreEqual(
            "Deleted 2 node(s) from draft with related connections. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsNotNull(viewModel.WorkflowDefinitionValidationErrorMessage);
        StringAssert.Contains(
            viewModel.WorkflowDefinitionValidationErrorMessage,
            "source_to_filter");
        StringAssert.Contains(
            viewModel.WorkflowDefinitionValidationErrorMessage,
            "filter_to_join");
        StringAssert.Contains(
            viewModel.WorkflowDefinitionValidationErrorMessage,
            "join_to_sink");
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual(0, viewModel.WorkflowDefinitionBatchSelectedNodeCount);
        Assert.IsFalse(viewModel.DeleteSelectedWorkflowDefinitionDraftNodesCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task NewDraftNodeInputUsesDefaultsAndResetsWhenDefinitionLoads()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        Assert.AreEqual(string.Empty, viewModel.NewDraftNodeInstanceId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftNodeType);
        Assert.AreEqual("1.0", viewModel.NewDraftNodeVersion);
        Assert.AreEqual(string.Empty, viewModel.NewDraftNodeDisplayName);
        Assert.AreEqual("{}", viewModel.NewDraftNodeConfigJson);

        viewModel.NewDraftNodeInstanceId = "stale";
        viewModel.NewDraftNodeType = "StaleNode";
        viewModel.NewDraftNodeVersion = "9.9";
        viewModel.NewDraftNodeDisplayName = "Stale";
        viewModel.NewDraftNodeConfigJson = """{"stale":true}""";

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual(string.Empty, viewModel.NewDraftNodeInstanceId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftNodeType);
        Assert.AreEqual("1.0", viewModel.NewDraftNodeVersion);
        Assert.AreEqual(string.Empty, viewModel.NewDraftNodeDisplayName);
        Assert.AreEqual("{}", viewModel.NewDraftNodeConfigJson);
        StringAssert.Contains(viewModel.WorkflowDefinitionDraftJson, "\"schema_version\": \"1.0\"");
        Assert.IsFalse(viewModel.IsWorkflowDefinitionDraftDirty);
    }

    [TestMethod]
    public async Task SelectingNewDraftNodeDefinitionFillsNodeInput()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition(
                        "GenerateTestTableNode",
                        "Generate Test Table",
                        schemaJson:
                            """
                            {
                              "type": "object",
                              "properties": {
                                "rows": {"type": "integer", "required": true, "default": 3},
                                "seed": {"type": "integer", "default": 0}
                              }
                            }
                            """),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        viewModel.SelectedNewDraftNodeDefinition = viewModel.NodeDefinitions.Single();

        Assert.AreEqual("GenerateTestTableNode", viewModel.NewDraftNodeType);
        Assert.AreEqual("1.0", viewModel.NewDraftNodeVersion);
        Assert.AreEqual("Generate Test Table", viewModel.NewDraftNodeDisplayName);
        Assert.AreEqual("generate_test_table", viewModel.NewDraftNodeInstanceId);
        using var config = JsonDocument.Parse(viewModel.NewDraftNodeConfigJson);
        Assert.AreEqual(3, config.RootElement.GetProperty("rows").GetInt32());
        Assert.AreEqual(0, config.RootElement.GetProperty("seed").GetInt32());
    }

    [TestMethod]
    public async Task SelectingNewDraftNodeDefinitionSuggestsUniqueNodeInstanceId()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "generate_test_table", "node_type": "GenerateTestTableNode", "node_version": "1.0"},
                {"node_instance_id": "generate_test_table_2", "node_type": "GenerateTestTableNode", "node_version": "1.0"}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition("GenerateTestTableNode", "Generate Test Table"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        viewModel.SelectedNewDraftNodeDefinition = viewModel.NodeDefinitions.Single();

        Assert.AreEqual("generate_test_table_3", viewModel.NewDraftNodeInstanceId);
    }

    [TestMethod]
    public async Task SelectingNewDraftNodeDefinitionDoesNotOverwriteManualNodeInstanceId()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition("FilterRowsNode", "Filter Rows"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);
        viewModel.NewDraftNodeInstanceId = "custom_filter";

        viewModel.SelectedNewDraftNodeDefinition = viewModel.NodeDefinitions.Single();

        Assert.AreEqual("FilterRowsNode", viewModel.NewDraftNodeType);
        Assert.AreEqual("1.0", viewModel.NewDraftNodeVersion);
        Assert.AreEqual("custom_filter", viewModel.NewDraftNodeInstanceId);
    }

    [TestMethod]
    public async Task SelectingNewDraftNodeDefinitionDoesNotOverwriteManualConfigJson()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition(
                        "GenerateTestTableNode",
                        "Generate Test Table",
                        schemaJson:
                            """
                            {
                              "type": "object",
                              "properties": {
                                "rows": {"type": "integer", "required": true, "default": 3}
                              }
                            }
                            """),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);
        viewModel.NewDraftNodeConfigJson = """{"custom":true}""";

        viewModel.SelectedNewDraftNodeDefinition = viewModel.NodeDefinitions.Single();

        Assert.AreEqual("""{"custom":true}""", viewModel.NewDraftNodeConfigJson);
    }

    [TestMethod]
    public async Task WorkflowAddNodePanelCommandsOpenCloseAndResetOnDefinitionReload()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        Assert.IsFalse(viewModel.OpenWorkflowAddNodePanelCommand.CanExecute(null));

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsTrue(viewModel.OpenWorkflowAddNodePanelCommand.CanExecute(null));

        viewModel.OpenWorkflowAddNodePanelCommand.Execute(null);

        Assert.IsTrue(viewModel.IsWorkflowAddNodePanelVisible);

        viewModel.CloseWorkflowAddNodePanelCommand.Execute(null);

        Assert.IsFalse(viewModel.IsWorkflowAddNodePanelVisible);

        viewModel.OpenWorkflowAddNodePanelCommand.Execute(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.IsWorkflowAddNodePanelVisible);
    }

    [TestMethod]
    public async Task AddWorkflowDefinitionDraftNodeCommandAddsNodeToDraft()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.OpenWorkflowAddNodePanelCommand.Execute(null);
        viewModel.NewDraftNodeInstanceId = "source";
        viewModel.NewDraftNodeType = "GenerateTestTableNode";
        viewModel.NewDraftNodeVersion = "1.0";
        viewModel.NewDraftNodeDisplayName = "Generate rows";
        viewModel.NewDraftNodeConfigJson = """{"rows":3}""";

        Assert.IsTrue(viewModel.IsWorkflowAddNodePanelVisible);
        Assert.IsTrue(viewModel.AddWorkflowDefinitionDraftNodeCommand.CanExecute(null));

        viewModel.AddWorkflowDefinitionDraftNodeCommand.Execute(null);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        var node = draft.RootElement.GetProperty("nodes")[0];
        Assert.AreEqual("source", node.GetProperty("node_instance_id").GetString());
        Assert.AreEqual("GenerateTestTableNode", node.GetProperty("node_type").GetString());
        Assert.AreEqual("Generate rows", node.GetProperty("display_name").GetString());
        Assert.AreEqual(3, node.GetProperty("config").GetProperty("rows").GetInt32());
        Assert.AreEqual("Node added to draft. Validate before saving.", viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftNodeCount);
        Assert.AreEqual("1 node(s)", viewModel.WorkflowDefinitionDraftNodeCountText);
        Assert.HasCount(1, viewModel.WorkflowDefinitionDraftNodes);
        Assert.AreEqual("source", viewModel.WorkflowDefinitionDraftNodes[0].NodeInstanceId);
        Assert.AreSame(viewModel.WorkflowDefinitionDraftNodes[0], viewModel.SelectedWorkflowDefinitionNode);
        Assert.AreEqual(string.Empty, viewModel.NewDraftNodeInstanceId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftNodeType);
        Assert.AreEqual("1.0", viewModel.NewDraftNodeVersion);
        Assert.AreEqual("{}", viewModel.NewDraftNodeConfigJson);
        Assert.IsFalse(viewModel.IsWorkflowAddNodePanelVisible);
    }

    [TestMethod]
    public async Task AddWorkflowDefinitionDraftNodeCommandInsertsAfterSelectedWorkflowNode()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": [
                {"connection_id": "keep", "source_node_id": "source", "source_port": "out", "target_node_id": "sink", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflowDefinitionNode =
            viewModel.WorkflowDefinitionDraftNodes.Single(node =>
                node.NodeInstanceId == "source");
        viewModel.NewDraftNodeInstanceId = "filter";
        viewModel.NewDraftNodeType = "FilterRowsNode";
        viewModel.NewDraftNodeVersion = "1.0";
        viewModel.NewDraftNodeConfigJson = """{"field":"amount"}""";

        viewModel.AddWorkflowDefinitionDraftNodeCommand.Execute(null);

        Assert.HasCount(3, viewModel.WorkflowDefinitionDraftNodes);
        Assert.AreEqual("source", viewModel.WorkflowDefinitionDraftNodes[0].NodeInstanceId);
        Assert.AreEqual("filter", viewModel.WorkflowDefinitionDraftNodes[1].NodeInstanceId);
        Assert.AreEqual("sink", viewModel.WorkflowDefinitionDraftNodes[2].NodeInstanceId);
        Assert.AreSame(
            viewModel.WorkflowDefinitionDraftNodes[1],
            viewModel.SelectedWorkflowDefinitionNode);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        var nodes = draft.RootElement.GetProperty("nodes");
        Assert.AreEqual("source", nodes[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("filter", nodes[1].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("sink", nodes[2].GetProperty("node_instance_id").GetString());
        Assert.AreEqual(1, draft.RootElement.GetProperty("connections").GetArrayLength());
        Assert.AreEqual(
            "keep",
            draft.RootElement
                .GetProperty("connections")[0]
                .GetProperty("connection_id")
                .GetString());
    }

    [TestMethod]
    public async Task AddWorkflowDefinitionDraftNodeCommandAutoWiresSingleLinearConnection()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": [
                {"connection_id": "source_to_sink", "source_node_id": "source", "source_port": "out", "target_node_id": "sink", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition(
                        "FilterRowsNode",
                        "Filter Rows",
                        inputPort: "in",
                        outputPort: "out"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflowDefinitionNode =
            viewModel.WorkflowDefinitionDraftNodes.Single(node =>
                node.NodeInstanceId == "source");
        viewModel.SelectedNewDraftNodeDefinition = viewModel.NodeDefinitions.Single();
        viewModel.NewDraftNodeInstanceId = "filter";
        viewModel.NewDraftNodeConfigJson = """{"field":"amount"}""";

        viewModel.AddWorkflowDefinitionDraftNodeCommand.Execute(null);

        Assert.AreEqual(
            "Node added to draft and linear connections were updated. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        var errorMessage = viewModel.WorkflowDefinitionValidationErrorMessage ?? string.Empty;
        StringAssert.Contains(errorMessage, "Removed:");
        StringAssert.Contains(errorMessage, "source_to_sink: source.out -> sink.in");
        StringAssert.Contains(errorMessage, "Added:");
        StringAssert.Contains(errorMessage, "source_to_filter: source.out -> filter.in");
        StringAssert.Contains(errorMessage, "filter_to_sink: filter.out -> sink.in");

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        var connections = draft.RootElement.GetProperty("connections");
        Assert.AreEqual(2, connections.GetArrayLength());
        Assert.AreEqual("source_to_filter", connections[0].GetProperty("connection_id").GetString());
        Assert.AreEqual("filter_to_sink", connections[1].GetProperty("connection_id").GetString());
    }

    [TestMethod]
    public async Task AddWorkflowDefinitionDraftNodeCommandRejectsInvalidConfigJson()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        var originalDraft = viewModel.WorkflowDefinitionDraftJson;
        viewModel.NewDraftNodeInstanceId = "source";
        viewModel.NewDraftNodeType = "GenerateTestTableNode";
        viewModel.NewDraftNodeVersion = "1.0";
        viewModel.NewDraftNodeConfigJson = "{";
        viewModel.IsWorkflowAddNodePanelVisible = true;

        Assert.IsTrue(viewModel.AddWorkflowDefinitionDraftNodeCommand.CanExecute(null));

        viewModel.AddWorkflowDefinitionDraftNodeCommand.Execute(null);

        Assert.AreEqual("Node add failed.", viewModel.WorkflowDefinitionValidationMessage);
        Assert.AreEqual(
            "Node config JSON is invalid.",
            viewModel.WorkflowDefinitionValidationErrorMessage);
        Assert.AreEqual(originalDraft, viewModel.WorkflowDefinitionDraftJson);
        Assert.AreEqual("source", viewModel.NewDraftNodeInstanceId);
        Assert.IsTrue(viewModel.IsWorkflowAddNodePanelVisible);
    }

    [TestMethod]
    public async Task AddWorkflowDefinitionDraftNodeCommandShowsDuplicateNodeError()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0"}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.NewDraftNodeInstanceId = "source";
        viewModel.NewDraftNodeType = "FilterRowsNode";
        viewModel.NewDraftNodeVersion = "1.0";
        viewModel.NewDraftNodeConfigJson = "{}";
        viewModel.IsWorkflowAddNodePanelVisible = true;

        viewModel.AddWorkflowDefinitionDraftNodeCommand.Execute(null);

        Assert.AreEqual("Node add failed.", viewModel.WorkflowDefinitionValidationMessage);
        Assert.AreEqual(
            "A node with this instance ID already exists.",
            viewModel.WorkflowDefinitionValidationErrorMessage);
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftNodeCount);
        Assert.AreEqual("source", viewModel.NewDraftNodeInstanceId);
        Assert.IsTrue(viewModel.IsWorkflowAddNodePanelVisible);
    }

    [TestMethod]
    public async Task CopyWorkflowDefinitionDraftNodeCommandCopiesSelectedNodeAfterSource()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "display_name": "Source rows", "config": {"rows": 3}},
                {"node_instance_id": "source_copy", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {"rows": 1}},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": [
                {"connection_id": "source_to_sink", "source_node_id": "source", "source_port": "out", "target_node_id": "sink", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflowDefinitionNode = null;

        Assert.IsFalse(viewModel.CopyWorkflowDefinitionDraftNodeCommand.CanExecute(null));

        viewModel.SelectedWorkflowDefinitionNode =
            viewModel.WorkflowDefinitionDraftNodes.Single(node =>
                node.NodeInstanceId == "source");

        Assert.IsTrue(viewModel.CopyWorkflowDefinitionDraftNodeCommand.CanExecute(null));

        viewModel.CopyWorkflowDefinitionDraftNodeCommand.Execute(null);

        Assert.AreEqual(
            "Node copied to draft. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual("source_copy_2", viewModel.SelectedWorkflowDefinitionNode?.NodeInstanceId);
        Assert.HasCount(4, viewModel.WorkflowDefinitionDraftNodes);
        Assert.AreEqual("source", viewModel.WorkflowDefinitionDraftNodes[0].NodeInstanceId);
        Assert.AreEqual("source_copy_2", viewModel.WorkflowDefinitionDraftNodes[1].NodeInstanceId);
        Assert.AreEqual("source_copy", viewModel.WorkflowDefinitionDraftNodes[2].NodeInstanceId);
        Assert.AreEqual("sink", viewModel.WorkflowDefinitionDraftNodes[3].NodeInstanceId);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        var nodes = draft.RootElement.GetProperty("nodes");
        var copied = nodes[1];
        Assert.AreEqual("source_copy_2", copied.GetProperty("node_instance_id").GetString());
        Assert.AreEqual("GenerateTestTableNode", copied.GetProperty("node_type").GetString());
        Assert.AreEqual("Source rows", copied.GetProperty("display_name").GetString());
        Assert.AreEqual(3, copied.GetProperty("config").GetProperty("rows").GetInt32());

        var connections = draft.RootElement.GetProperty("connections");
        Assert.AreEqual(1, connections.GetArrayLength());
        Assert.AreEqual(
            "source_to_sink",
            connections[0].GetProperty("connection_id").GetString());
        Assert.AreEqual("source", connections[0].GetProperty("source_node_id").GetString());
        Assert.AreEqual("sink", connections[0].GetProperty("target_node_id").GetString());
    }

    [TestMethod]
    public async Task SelectedWorkflowDefinitionDraftNodeInputResetsAndClearsWhenDraftChanges()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0"}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedWorkflowDefinitionDraftNodeInstanceId = "stale";

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual(string.Empty, viewModel.SelectedWorkflowDefinitionDraftNodeInstanceId);

        viewModel.SelectedWorkflowDefinitionDraftNodeInstanceId = "source";

        Assert.AreEqual("source", viewModel.SelectedWorkflowDefinitionDraftNodeInstanceId);

        viewModel.WorkflowDefinitionDraftJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [],
              "connections": []
            }
            """;

        Assert.AreEqual(string.Empty, viewModel.SelectedWorkflowDefinitionDraftNodeInstanceId);
    }

    [TestMethod]
    public async Task DeleteWorkflowDefinitionDraftNodeCommandDeletesUnconnectedNode()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0"},
                {"node_instance_id": "orphan", "node_type": "FilterRowsNode", "node_version": "1.0"}
              ],
              "connections": [
                {"connection_id": "keep", "source_node_id": "source", "source_port": "out", "target_node_id": "source", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        viewModel.SelectedWorkflowDefinitionNode = null;

        Assert.IsFalse(viewModel.DeleteWorkflowDefinitionDraftNodeCommand.CanExecute(null));

        viewModel.SelectedWorkflowDefinitionNode =
            viewModel.WorkflowDefinitionDraftNodes.Single(node =>
                node.NodeInstanceId == "orphan");

        Assert.IsTrue(viewModel.DeleteWorkflowDefinitionDraftNodeCommand.CanExecute(null));

        viewModel.DeleteWorkflowDefinitionDraftNodeCommand.Execute(null);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        Assert.AreEqual(1, draft.RootElement.GetProperty("nodes").GetArrayLength());
        Assert.AreEqual(
            "source",
            draft.RootElement.GetProperty("nodes")[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual(1, draft.RootElement.GetProperty("connections").GetArrayLength());
        Assert.AreEqual(
            "Node deleted from draft. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftNodeCount);
        Assert.HasCount(1, viewModel.WorkflowDefinitionDraftNodes);
        Assert.AreEqual("source", viewModel.WorkflowDefinitionDraftNodes[0].NodeInstanceId);
        Assert.IsNull(viewModel.SelectedWorkflowDefinitionNode);
        Assert.IsFalse(viewModel.DeleteWorkflowDefinitionDraftNodeCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task MoveWorkflowDefinitionDraftNodeCommandsReorderSelectedNode()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "filter", "node_type": "FilterRowsNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflowDefinitionNode =
            viewModel.WorkflowDefinitionDraftNodes.Single(node =>
                node.NodeInstanceId == "filter");

        Assert.IsTrue(viewModel.MoveSelectedWorkflowDefinitionDraftNodeUpCommand.CanExecute(null));
        Assert.IsTrue(viewModel.MoveSelectedWorkflowDefinitionDraftNodeDownCommand.CanExecute(null));

        viewModel.MoveSelectedWorkflowDefinitionDraftNodeUpCommand.Execute(null);

        Assert.AreEqual(
            "Node list order updated; connections are unchanged. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual("filter", viewModel.WorkflowDefinitionDraftNodes[0].NodeInstanceId);
        Assert.AreEqual("filter", viewModel.SelectedWorkflowDefinitionNode?.NodeInstanceId);
        Assert.IsFalse(viewModel.MoveSelectedWorkflowDefinitionDraftNodeUpCommand.CanExecute(null));
        Assert.IsTrue(viewModel.MoveSelectedWorkflowDefinitionDraftNodeDownCommand.CanExecute(null));

        viewModel.MoveSelectedWorkflowDefinitionDraftNodeDownCommand.Execute(null);

        Assert.AreEqual("source", viewModel.WorkflowDefinitionDraftNodes[0].NodeInstanceId);
        Assert.AreEqual("filter", viewModel.WorkflowDefinitionDraftNodes[1].NodeInstanceId);
        Assert.AreEqual("filter", viewModel.SelectedWorkflowDefinitionNode?.NodeInstanceId);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        Assert.AreEqual("source", draft.RootElement.GetProperty("nodes")[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("filter", draft.RootElement.GetProperty("nodes")[1].GetProperty("node_instance_id").GetString());
        Assert.AreEqual(1, draft.RootElement.GetProperty("connections").GetArrayLength());
        var connection = draft.RootElement.GetProperty("connections")[0];
        Assert.AreEqual(
            "source_to_filter",
            connection.GetProperty("connection_id").GetString());
        Assert.AreEqual("source", connection.GetProperty("source_node_id").GetString());
        Assert.AreEqual("out", connection.GetProperty("source_port").GetString());
        Assert.AreEqual("filter", connection.GetProperty("target_node_id").GetString());
        Assert.AreEqual("in", connection.GetProperty("target_port").GetString());
    }

    [TestMethod]
    public async Task WorkflowDefinitionNodeActionDisabledReasonsReflectSelectionAndBoundaries()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0", "config": {}},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0", "config": {}}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        Assert.AreEqual(
            "Action is disabled because no workflow definition is loaded.",
            viewModel.CopyWorkflowDefinitionDraftNodeDisabledReasonText);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual("source", viewModel.SelectedWorkflowDefinitionNode?.NodeInstanceId);
        Assert.IsNull(viewModel.CopyWorkflowDefinitionDraftNodeDisabledReasonText);
        Assert.IsNull(viewModel.DeleteWorkflowDefinitionDraftNodeDisabledReasonText);
        Assert.AreEqual(
            "The selected node is already at the top of the list.",
            viewModel.MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText);
        Assert.IsNull(viewModel.MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText);
        Assert.AreEqual(
            "Action is disabled because no workflow nodes are checked.",
            viewModel.DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText);

        viewModel.WorkflowDefinitionDraftNodes[0].IsBatchSelected = true;

        Assert.IsNull(viewModel.DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText);

        viewModel.SelectedWorkflowDefinitionNode = viewModel.WorkflowDefinitionDraftNodes[1];

        Assert.IsNull(viewModel.MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText);
        Assert.AreEqual(
            "The selected node is already at the bottom of the list.",
            viewModel.MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText);

        viewModel.SelectedWorkflowDefinitionNode = null;

        Assert.AreEqual(
            "Action is disabled because no workflow node is selected.",
            viewModel.CopyWorkflowDefinitionDraftNodeDisabledReasonText);
        Assert.AreEqual(
            "Action is disabled because no workflow node is selected.",
            viewModel.DeleteWorkflowDefinitionDraftNodeDisabledReasonText);
        Assert.AreEqual(
            "Action is disabled because no workflow node is selected.",
            viewModel.MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText);
    }

    [TestMethod]
    public async Task DeleteWorkflowDefinitionDraftNodeCommandDeletesConnectedNodeAndRelatedConnections()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0"},
                {"node_instance_id": "filter", "node_type": "FilterRowsNode", "node_version": "1.0"},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0"}
              ],
              "connections": [
                {"connection_id": "c1", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"},
                {"connection_id": "c2", "source_node_id": "filter", "source_port": "out", "target_node_id": "sink", "target_port": "in"},
                {"connection_id": "keep", "source_node_id": "source", "source_port": "out", "target_node_id": "sink", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflowDefinitionNode =
            viewModel.WorkflowDefinitionDraftNodes.Single(node =>
                node.NodeInstanceId == "filter");

        viewModel.DeleteWorkflowDefinitionDraftNodeCommand.Execute(null);

        Assert.AreEqual(
            "Node deleted from draft with related connections. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        var errorMessage = viewModel.WorkflowDefinitionValidationErrorMessage ?? string.Empty;
        StringAssert.Contains(
            errorMessage,
            "Removed related connections:",
            "Delete should explain which related connections were removed.");
        StringAssert.Contains(
            errorMessage,
            "c1: source.out -> filter.in",
            "Delete should show the removed upstream connection endpoints.");
        StringAssert.Contains(
            errorMessage,
            "c2: filter.out -> sink.in",
            "Delete should show the removed downstream connection endpoints.");
        Assert.AreEqual(2, viewModel.WorkflowDefinitionDraftNodeCount);
        Assert.HasCount(2, viewModel.WorkflowDefinitionDraftNodes);
        Assert.IsFalse(viewModel.WorkflowDefinitionDraftNodes.Any(node =>
            node.NodeInstanceId == "filter"));
        Assert.IsNull(viewModel.SelectedWorkflowDefinitionNode);
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        Assert.AreEqual(2, draft.RootElement.GetProperty("nodes").GetArrayLength());
        Assert.AreEqual(1, draft.RootElement.GetProperty("connections").GetArrayLength());
        Assert.AreEqual(
            "keep",
            draft.RootElement
                .GetProperty("connections")[0]
                .GetProperty("connection_id")
                .GetString());
    }

    [TestMethod]
    public async Task DeleteWorkflowDefinitionDraftNodeCommandBridgesLinearMiddleNodeConnections()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode", "node_version": "1.0"},
                {"node_instance_id": "filter", "node_type": "FilterRowsNode", "node_version": "1.0"},
                {"node_instance_id": "sink", "node_type": "PublishSharedTablesNode", "node_version": "1.0"}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"},
                {"connection_id": "filter_to_sink", "source_node_id": "filter", "source_port": "out", "target_node_id": "sink", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflowDefinitionNode =
            viewModel.WorkflowDefinitionDraftNodes.Single(node =>
                node.NodeInstanceId == "filter");

        viewModel.DeleteWorkflowDefinitionDraftNodeCommand.Execute(null);

        Assert.AreEqual(
            "Node deleted from draft and linear connections were updated. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        var message = viewModel.WorkflowDefinitionValidationErrorMessage ?? string.Empty;
        StringAssert.Contains(message, "Updated connections:");
        StringAssert.Contains(message, "source_to_filter: source.out -> filter.in");
        StringAssert.Contains(message, "filter_to_sink: filter.out -> sink.in");
        StringAssert.Contains(message, "source_to_sink: source.out -> sink.in");

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        var nodes = draft.RootElement.GetProperty("nodes");
        Assert.AreEqual(2, nodes.GetArrayLength());
        Assert.AreEqual("source", nodes[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("sink", nodes[1].GetProperty("node_instance_id").GetString());

        var connections = draft.RootElement.GetProperty("connections");
        Assert.AreEqual(1, connections.GetArrayLength());
        Assert.AreEqual(
            "source_to_sink",
            connections[0].GetProperty("connection_id").GetString());
        Assert.AreEqual("source", connections[0].GetProperty("source_node_id").GetString());
        Assert.AreEqual("sink", connections[0].GetProperty("target_node_id").GetString());
    }

    [TestMethod]
    public async Task DraftConnectionInputResetsAndSelectedConnectionClearsWhenDraftChanges()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.NewDraftConnectionId = "stale";
        viewModel.NewDraftConnectionSourceNodeId = "old-source";
        viewModel.NewDraftConnectionSourcePort = "old-out";
        viewModel.NewDraftConnectionTargetNodeId = "old-target";
        viewModel.NewDraftConnectionTargetPort = "old-in";
        viewModel.SelectedWorkflowDefinitionDraftConnectionId = "stale-connection";

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionSourceNodeId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionSourcePort);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionTargetNodeId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionTargetPort);
        Assert.AreEqual(string.Empty, viewModel.SelectedWorkflowDefinitionDraftConnectionId);

        viewModel.SelectedWorkflowDefinitionDraftConnectionId = "source_to_filter";

        Assert.AreEqual(
            "source_to_filter",
            viewModel.SelectedWorkflowDefinitionDraftConnectionId);

        viewModel.WorkflowDefinitionDraftJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": []
            }
            """;

        Assert.AreEqual(string.Empty, viewModel.SelectedWorkflowDefinitionDraftConnectionId);
    }

    [TestMethod]
    public async Task SelectingNewDraftConnectionNodesFillsEndpointsAndSuggestsConnectionId()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedNewDraftConnectionSourceNode =
            viewModel.WorkflowDefinitionDraftStructure?.Nodes.Single(node =>
                node.NodeInstanceId == "source");
        viewModel.SelectedNewDraftConnectionTargetNode =
            viewModel.WorkflowDefinitionDraftStructure?.Nodes.Single(node =>
                node.NodeInstanceId == "filter");

        Assert.AreEqual("source", viewModel.NewDraftConnectionSourceNodeId);
        Assert.AreEqual("filter", viewModel.NewDraftConnectionTargetNodeId);
        Assert.AreEqual("source_to_filter", viewModel.NewDraftConnectionId);
    }

    [TestMethod]
    public async Task SelectingNewDraftConnectionNodesSuggestsUniqueConnectionId()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"},
                {"connection_id": "source_to_filter_2", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedNewDraftConnectionSourceNode =
            viewModel.WorkflowDefinitionDraftStructure?.Nodes.Single(node =>
                node.NodeInstanceId == "source");
        viewModel.SelectedNewDraftConnectionTargetNode =
            viewModel.WorkflowDefinitionDraftStructure?.Nodes.Single(node =>
                node.NodeInstanceId == "filter");

        Assert.AreEqual("source_to_filter_3", viewModel.NewDraftConnectionId);
    }

    [TestMethod]
    public async Task SelectingNewDraftConnectionNodesDoesNotOverwriteManualConnectionId()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.NewDraftConnectionId = "custom_link";
        viewModel.SelectedNewDraftConnectionSourceNode =
            viewModel.WorkflowDefinitionDraftStructure?.Nodes.Single(node =>
                node.NodeInstanceId == "source");
        viewModel.SelectedNewDraftConnectionTargetNode =
            viewModel.WorkflowDefinitionDraftStructure?.Nodes.Single(node =>
                node.NodeInstanceId == "filter");

        Assert.AreEqual("source", viewModel.NewDraftConnectionSourceNodeId);
        Assert.AreEqual("filter", viewModel.NewDraftConnectionTargetNodeId);
        Assert.AreEqual("custom_link", viewModel.NewDraftConnectionId);
    }

    [TestMethod]
    public async Task AddWorkflowDefinitionDraftConnectionCommandAddsConnectionToDraft()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.NewDraftConnectionId = "source_to_filter";
        viewModel.NewDraftConnectionSourceNodeId = "source";
        viewModel.NewDraftConnectionSourcePort = "out";
        viewModel.NewDraftConnectionTargetNodeId = "filter";
        viewModel.NewDraftConnectionTargetPort = "in";

        Assert.IsTrue(viewModel.AddWorkflowDefinitionDraftConnectionCommand.CanExecute(null));

        viewModel.AddWorkflowDefinitionDraftConnectionCommand.Execute(null);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        var connection = draft.RootElement.GetProperty("connections")[0];
        Assert.AreEqual("source_to_filter", connection.GetProperty("connection_id").GetString());
        Assert.AreEqual("source", connection.GetProperty("source_node_id").GetString());
        Assert.AreEqual("out", connection.GetProperty("source_port").GetString());
        Assert.AreEqual("filter", connection.GetProperty("target_node_id").GetString());
        Assert.AreEqual("in", connection.GetProperty("target_port").GetString());
        Assert.AreEqual(
            "Connection added to draft. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftConnectionCount);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionSourceNodeId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionSourcePort);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionTargetNodeId);
        Assert.AreEqual(string.Empty, viewModel.NewDraftConnectionTargetPort);
    }

    [TestMethod]
    public async Task AddWorkflowDefinitionDraftConnectionCommandShowsEndpointError()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"}
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.NewDraftConnectionId = "source_to_filter";
        viewModel.NewDraftConnectionSourceNodeId = "source";
        viewModel.NewDraftConnectionSourcePort = "out";
        viewModel.NewDraftConnectionTargetNodeId = "filter";
        viewModel.NewDraftConnectionTargetPort = "in";

        viewModel.AddWorkflowDefinitionDraftConnectionCommand.Execute(null);

        Assert.AreEqual("Connection add failed.", viewModel.WorkflowDefinitionValidationMessage);
        Assert.AreEqual(
            "Target node was not found in the draft.",
            viewModel.WorkflowDefinitionValidationErrorMessage);
        Assert.AreEqual(0, viewModel.WorkflowDefinitionDraftConnectionCount);
        Assert.AreEqual("source_to_filter", viewModel.NewDraftConnectionId);
    }

    [TestMethod]
    public async Task AddWorkflowDefinitionDraftConnectionCommandShowsDuplicateConnectionError()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.NewDraftConnectionId = "source_to_filter";
        viewModel.NewDraftConnectionSourceNodeId = "source";
        viewModel.NewDraftConnectionSourcePort = "out";
        viewModel.NewDraftConnectionTargetNodeId = "filter";
        viewModel.NewDraftConnectionTargetPort = "in";

        viewModel.AddWorkflowDefinitionDraftConnectionCommand.Execute(null);

        Assert.AreEqual("Connection add failed.", viewModel.WorkflowDefinitionValidationMessage);
        Assert.AreEqual(
            "A connection with this ID already exists.",
            viewModel.WorkflowDefinitionValidationErrorMessage);
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftConnectionCount);
        Assert.AreEqual("source_to_filter", viewModel.NewDraftConnectionId);
    }

    [TestMethod]
    public async Task DeleteWorkflowDefinitionDraftConnectionCommandDeletesConnection()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": [
                {"connection_id": "remove", "source_node_id": "source", "source_port": "out", "target_node_id": "filter", "target_port": "in"},
                {"connection_id": "keep", "source_node_id": "source", "source_port": "out", "target_node_id": "source", "target_port": "in"}
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.DeleteWorkflowDefinitionDraftConnectionCommand.CanExecute(null));

        viewModel.SelectedWorkflowDefinitionDraftConnectionId = "remove";

        Assert.IsTrue(viewModel.DeleteWorkflowDefinitionDraftConnectionCommand.CanExecute(null));

        viewModel.DeleteWorkflowDefinitionDraftConnectionCommand.Execute(null);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        Assert.AreEqual(1, draft.RootElement.GetProperty("connections").GetArrayLength());
        Assert.AreEqual(
            "keep",
            draft.RootElement.GetProperty("connections")[0].GetProperty("connection_id").GetString());
        Assert.AreEqual(
            "Connection deleted from draft. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftConnectionCount);
        Assert.AreEqual(string.Empty, viewModel.SelectedWorkflowDefinitionDraftConnectionId);
    }

    [TestMethod]
    public async Task LoadSelectedWorkflowDefinitionMarksUnknownNodesAsUnregisteredJsonFallback()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "custom",
                  "node_type": "CustomNode",
                  "node_version": "1.0",
                  "display_name": "Custom Node",
                  "config": {"enabled": true}
                }
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        var node = viewModel.WorkflowDefinitionDetail?.Nodes[0];
        Assert.IsNotNull(node);
        Assert.AreEqual("CustomNode", node.NodeType);
        Assert.AreEqual("Custom Node", node.NodeEditorResolution.DisplayName);
        Assert.AreEqual(NodeEditorKind.JsonFallback, node.NodeEditorResolution.Kind);
        Assert.IsFalse(node.HasRegisteredNodeEditor);
        Assert.IsTrue(node.UsesJsonFallback);
        Assert.AreEqual(
            NodeEditorResolution.UnregisteredJsonFallbackStatusKey,
            node.NodeEditorResolution.StatusKey);
        Assert.AreEqual("Not registered, JSON fallback", node.NodeEditorStatusText);
    }

    [TestMethod]
    public async Task ValidateWorkflowDefinitionDraftSendsCurrentDraftJson()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            ValidateWorkflowDraftResponse =
                ApiResponseEnvelope<WorkflowValidationResultDto>.Success(
                    new WorkflowValidationResultDto { Valid = true }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.WorkflowDefinitionDraftJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [{"node_instance_id": "a", "node_type": "GenerateTestTableNode", "node_version": "1.0"}],
              "connections": []
            }
            """;

        await viewModel.ValidateWorkflowDefinitionDraftCommand.ExecuteAsync(null);

        Assert.IsNotNull(apiClient.ValidatedWorkflowDraftDefinition);
        Assert.AreEqual(
            "a",
            apiClient.ValidatedWorkflowDraftDefinition.Value
                .GetProperty("nodes")[0]
                .GetProperty("node_instance_id")
                .GetString());
        Assert.AreEqual("Workflow draft is valid.", viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
    }

    [TestMethod]
    public async Task ValidateWorkflowDefinitionDraftRejectsInvalidJsonBeforeApi()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1)),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.WorkflowDefinitionDraftJson = "{";

        await viewModel.ValidateWorkflowDefinitionDraftCommand.ExecuteAsync(null);

        Assert.IsNull(apiClient.ValidatedWorkflowDraftDefinition);
        Assert.AreEqual("Workflow draft JSON is invalid.", viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsTrue(viewModel.HasWorkflowDefinitionValidationError);
    }

    [TestMethod]
    public async Task ValidateWorkflowDefinitionDraftShowsBackendIssues()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1)),
            ValidateWorkflowDraftResponse =
                ApiResponseEnvelope<WorkflowValidationResultDto>.Success(
                    new WorkflowValidationResultDto
                    {
                        Valid = false,
                        Errors =
                        [
                            new WorkflowValidationIssueDto
                            {
                                Code = "UNKNOWN_NODE_TYPE",
                                Path = "nodes[0]",
                                Message = "Unknown node type/version: Missing@1.0",
                            },
                        ],
                    }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.ValidateWorkflowDefinitionDraftCommand.ExecuteAsync(null);

        Assert.AreEqual(
            "Workflow draft has validation issues.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.AreEqual(
            "UNKNOWN_NODE_TYPE at nodes[0]: Unknown node type/version: Missing@1.0",
            viewModel.WorkflowDefinitionValidationErrorMessage);
    }

    [TestMethod]
    public async Task SaveWorkflowDefinitionDraftUsesLoadedRevisionAndRefreshesDetail()
    {
        var v1Json =
            """
            {"schema_version":"1.0","nodes":[],"connections":[]}
            """;
        var v2Json =
            """
            {"schema_version":"1.0","nodes":[{"node_instance_id":"a","node_type":"GenerateTestTableNode","node_version":"1.0"}],"connections":[]}
            """;
        var v1 = Workflow("wf-1", "Daily Load", 1, v1Json);
        var v2 = Workflow("wf-1", "Daily Load", 2, v2Json) with
        {
            RevisionId = "rev-wf-1-v2",
            DefinitionHash = "hash-wf-1-v2",
        };
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { v1 }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(v1),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto> { Revision("rev-wf-1", "wf-1", 1, v1Json) }),
            UpdateWorkflowResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(v2),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.WorkflowDefinitionDraftJson = v2Json;
        apiClient.WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
            new List<WorkflowDefinitionDto> { v2 });
        apiClient.WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(v2);
        apiClient.WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
            new List<WorkflowRevisionDto>
            {
                Revision("rev-wf-1", "wf-1", 1, v1Json),
                Revision("rev-wf-1-v2", "wf-1", 2, v2Json),
            });

        await viewModel.SaveWorkflowDefinitionDraftCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", apiClient.UpdatedWorkflowId);
        Assert.AreEqual("Daily Load", apiClient.UpdatedWorkflowName);
        Assert.AreEqual("rev-wf-1", apiClient.UpdatedWorkflowBaseRevisionId);
        Assert.IsNotNull(apiClient.UpdatedWorkflowDefinition);
        Assert.AreEqual(
            "a",
            apiClient.UpdatedWorkflowDefinition.Value
                .GetProperty("nodes")[0]
                .GetProperty("node_instance_id")
                .GetString());
        Assert.AreEqual("rev-wf-1-v2", viewModel.WorkflowDefinitionDetail?.RevisionId);
        Assert.AreEqual("Loaded Daily Load v2.", viewModel.WorkflowDefinitionMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
    }

    [TestMethod]
    public async Task SaveWorkflowDefinitionDraftShowsRevisionConflict()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1)),
            UpdateWorkflowResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "WORKFLOW_REVISION_CONFLICT",
                "Workflow revision has changed."),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.WorkflowDefinitionDraftJson = """{"nodes":[],"connections":[]}""";
        await viewModel.SaveWorkflowDefinitionDraftCommand.ExecuteAsync(null);

        Assert.AreEqual("Workflow draft save failed.", viewModel.WorkflowDefinitionValidationMessage);
        Assert.AreEqual(
            "Revision conflict: the workflow has been modified by another session.",
            viewModel.WorkflowDefinitionValidationErrorMessage);
        Assert.IsTrue(viewModel.HasWorkflowDefinitionValidationError);
        Assert.IsTrue(viewModel.HasWorkflowDefinitionRevisionConflict);
        Assert.AreEqual("""{"nodes":[],"connections":[]}""", viewModel.WorkflowDefinitionDraftJson);

        viewModel.WorkflowDefinitionDraftJson = """{"nodes":[],"connections":[],"metadata":{"note":"keep draft"}}""";
        viewModel.NewDraftNodeInstanceId = "source";
        viewModel.NewDraftNodeType = "GenerateTestTableNode";
        viewModel.NewDraftNodeVersion = "1.0";
        viewModel.NewDraftNodeConfigJson = "{}";
        viewModel.SelectedWorkflowDefinitionDraftNodeInstanceId = "source";
        viewModel.NewDraftConnectionId = "c1";
        viewModel.NewDraftConnectionSourceNodeId = "source";
        viewModel.NewDraftConnectionSourcePort = "out";
        viewModel.NewDraftConnectionTargetNodeId = "target";
        viewModel.NewDraftConnectionTargetPort = "in";
        viewModel.SelectedWorkflowDefinitionDraftConnectionId = "c1";

        Assert.IsTrue(viewModel.HasWorkflowDefinitionRevisionConflict);
        Assert.IsFalse(viewModel.SaveWorkflowDefinitionDraftCommand.CanExecute(null));
        Assert.IsFalse(viewModel.AddWorkflowDefinitionDraftNodeCommand.CanExecute(null));
        Assert.IsFalse(viewModel.DeleteWorkflowDefinitionDraftNodeCommand.CanExecute(null));
        Assert.IsFalse(viewModel.AddWorkflowDefinitionDraftConnectionCommand.CanExecute(null));
        Assert.IsFalse(viewModel.DeleteWorkflowDefinitionDraftConnectionCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task WorkflowDefinitionEditSaveAndRunLoopUsesCurrentRevision()
    {
        var v1Json =
            """
            {"schema_version":"1.0","nodes":[],"connections":[]}
            """;
        var v2Json =
            """
            {"schema_version":"1.0","nodes":[{"node_instance_id":"generate","node_type":"GenerateTestTableNode","node_version":"1.0","config":{"rows":3}}],"connections":[]}
            """;
        var created = Workflow("wf-loop", "Generated table workflow", 1, v1Json) with
        {
            RevisionId = "rev-loop-v1",
            DefinitionHash = "hash-loop-v1",
        };
        var saved = Workflow("wf-loop", "Generated table workflow", 2, v2Json) with
        {
            RevisionId = "rev-loop-v2",
            DefinitionHash = "hash-loop-v2",
        };
        var apiClient = new FakeApiClient
        {
            CreateWorkflowResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(created),
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { created }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(created),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>
                {
                    Revision("rev-loop-v1", "wf-loop", 1, v1Json),
                }),
            ValidateWorkflowDraftResponse =
                ApiResponseEnvelope<WorkflowValidationResultDto>.Success(
                    new WorkflowValidationResultDto { Valid = true }),
            UpdateWorkflowResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(saved),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
                new WorkflowRunDto
                {
                    WorkflowRunId = "run-loop",
                    WorkflowId = "wf-loop",
                    RevisionId = "rev-loop-v2",
                    WorkflowVersion = 2,
                    DefinitionHash = "hash-loop-v2",
                    Status = "PENDING",
                }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto>
                {
                    Run("run-loop", "wf-loop", "PENDING") with
                    {
                        RevisionId = "rev-loop-v2",
                        WorkflowVersion = 2,
                        DefinitionHash = "hash-loop-v2",
                    },
                }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-loop", "run-loop", "generate", "READY", 0, "waiting"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.CreateTemplateWorkflowCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.WorkflowDefinitionDraftJson = v2Json;
        await viewModel.ValidateWorkflowDefinitionDraftCommand.ExecuteAsync(null);

        apiClient.WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
            new List<WorkflowDefinitionDto> { saved });
        apiClient.WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(saved);
        apiClient.WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
            new List<WorkflowRevisionDto>
            {
                Revision("rev-loop-v1", "wf-loop", 1, v1Json),
                Revision("rev-loop-v2", "wf-loop", 2, v2Json),
            });

        await viewModel.SaveWorkflowDefinitionDraftCommand.ExecuteAsync(null);
        await viewModel.StartSelectedWorkflowCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeRunsCommand.ExecuteAsync(null);

        Assert.AreEqual("Generated table workflow", apiClient.CreatedWorkflowName);
        Assert.AreEqual("rev-loop-v1", apiClient.UpdatedWorkflowBaseRevisionId);
        Assert.AreEqual("wf-loop", apiClient.StartedWorkflowId);
        Assert.AreEqual("rev-loop-v2", viewModel.WorkflowDefinitionDetail?.RevisionId);
        Assert.AreEqual("run-loop", viewModel.LastStartedRunId);
        Assert.AreEqual("PENDING", viewModel.LastStartedRunStatus);
        Assert.AreEqual("run-loop", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("generate", viewModel.NodeRuns[0].NodeInstanceId);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
        Assert.IsFalse(viewModel.HasRunError);
        Assert.IsFalse(viewModel.HasNodeRunError);
    }

    [TestMethod]
    public async Task LoadSelectedWorkflowDefinitionShowsErrorEnvelope()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "WORKFLOW_NOT_FOUND",
                "Workflow not found."),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.HasWorkflowDefinition);
        Assert.IsTrue(viewModel.HasWorkflowDefinitionError);
        Assert.AreEqual("Workflow definition load failed.", viewModel.WorkflowDefinitionMessage);
        Assert.AreEqual("WORKFLOW_NOT_FOUND: Workflow not found.", viewModel.WorkflowDefinitionErrorMessage);
    }

    [TestMethod]
    public async Task RefreshNodeDefinitionsLoadsReadOnlyCatalog()
    {
        var apiClient = new FakeApiClient
        {
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition("FilterRowsNode", "Filter Rows", inputPort: "in"),
                    NodeDefinition("GenerateTestTableNode", "Generate Test Table", outputPort: "out"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        Assert.HasCount(2, viewModel.NodeDefinitions);
        Assert.AreEqual("FilterRowsNode", viewModel.NodeDefinitions[0].NodeType);
        Assert.AreEqual("in*", viewModel.NodeDefinitions[0].InputPortsText);
        Assert.AreEqual("GenerateTestTableNode", viewModel.NodeDefinitions[1].NodeType);
        Assert.AreEqual("out", viewModel.NodeDefinitions[1].OutputPortsText);
        Assert.AreEqual("Loaded 2 node definition(s).", viewModel.NodeDefinitionCatalogMessage);
        Assert.IsFalse(viewModel.HasNodeDefinitionCatalogError);
        Assert.IsTrue(viewModel.HasNodeDefinitions);
        Assert.IsFalse(viewModel.HasNodeDefinitionCatalogEmptyState);
        Assert.AreEqual("secret", apiClient.LastSettings?.Token);
    }

    [TestMethod]
    public async Task SelectedNodeConfigDraftSummaryUsesLoadedNodeSchema()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {"field": "amount", "operator": "GT"}
                }
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition(
                        "FilterRowsNode",
                        "Filter Rows",
                        schemaJson:
                            """
                            {
                              "type": "object",
                              "properties": {
                                "field": {"type": "string", "required": true},
                                "operator": {"type": "enum", "enum": ["GT", "LT"]},
                                "columns": {"type": "array", "items": {"type": "string"}}
                              }
                            }
                            """),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual(
            "Selected node config schema unavailable.",
            viewModel.SelectedNodeConfigDraftSummaryText);
        Assert.IsNotNull(viewModel.SelectedNodeConfigDraft);
        Assert.IsFalse(viewModel.SelectedNodeConfigDraft.IsSupported);
        Assert.IsNull(viewModel.SelectedNodeConfigEditableDraft);
        Assert.IsFalse(viewModel.ApplySelectedNodeConfigDraftCommand.CanExecute(null));

        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        Assert.AreEqual(
            "filter: 2 editable config field(s), 1 JSON fallback field(s)",
            viewModel.SelectedNodeConfigDraftSummaryText);
        Assert.IsNotNull(viewModel.SelectedNodeConfigDraft);
        Assert.IsTrue(viewModel.SelectedNodeConfigDraft.IsSupported);
        Assert.IsNotNull(viewModel.SelectedNodeConfigEditableDraft);
        Assert.HasCount(2, viewModel.SelectedNodeConfigEditableDraft.Fields);
        Assert.IsTrue(viewModel.HasSelectedNodeConfigEditableInputFields);
        Assert.HasCount(2, viewModel.SelectedNodeConfigEditableInputFields);
        Assert.IsTrue(viewModel.ApplySelectedNodeConfigDraftCommand.CanExecute(null));
        Assert.AreEqual(
            "amount",
            viewModel.SelectedNodeConfigEditableDraft.Fields
                .Single(field => field.Name == "field")
                .InputValue);
        var fieldInput = viewModel.SelectedNodeConfigEditableInputFields
            .Single(field => field.Name == "field");
        Assert.AreEqual("amount", fieldInput.InputValue);
        Assert.IsFalse(fieldInput.IsDirty);
        CollectionAssert.AreEqual(
            new[] { "GT", "LT" },
            viewModel.SelectedNodeConfigEditableDraft.Fields
                .Single(field => field.Name == "operator")
                .EnumValues
                .ToArray());

        fieldInput.InputValue = "total";

        Assert.IsTrue(fieldInput.IsDirty);
    }

    [TestMethod]
    public async Task SelectedNodeConfigEditableDraftRefreshesWhenSelectionOrDraftJsonChanges()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "filter-a",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {"field": "amount"}
                },
                {
                  "node_instance_id": "filter-b",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {"field": "status"}
                }
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition(
                        "FilterRowsNode",
                        "Filter Rows",
                        schemaJson:
                            """
                            {
                              "type": "object",
                              "properties": {
                                "field": {"type": "string", "required": true}
                              }
                            }
                            """),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        Assert.AreEqual("filter-a", viewModel.SelectedWorkflowDefinitionNode?.NodeInstanceId);
        Assert.AreEqual(
            "amount",
            viewModel.SelectedNodeConfigEditableDraft?.Fields.Single().InputValue);
        Assert.AreEqual(
            "amount",
            viewModel.SelectedNodeConfigEditableInputFields.Single().InputValue);

        viewModel.SelectedWorkflowDefinitionNode = viewModel.WorkflowDefinitionDetail?.Nodes[1];

        Assert.AreEqual("filter-b", viewModel.SelectedWorkflowDefinitionNode?.NodeInstanceId);
        Assert.AreEqual(
            "status",
            viewModel.SelectedNodeConfigEditableDraft?.Fields.Single().InputValue);
        Assert.AreEqual(
            "status",
            viewModel.SelectedNodeConfigEditableInputFields.Single().InputValue);

        viewModel.WorkflowDefinitionDraftJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "filter-a",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {"field": "amount"}
                },
                {
                  "node_instance_id": "filter-b",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {"field": "state"}
                }
              ],
              "connections": []
            }
            """;

        Assert.AreEqual(
            "state",
            viewModel.SelectedNodeConfigEditableDraft?.Fields.Single().InputValue);
        Assert.AreEqual(
            "state",
            viewModel.SelectedNodeConfigEditableInputFields.Single().InputValue);
        Assert.IsFalse(viewModel.SelectedNodeConfigEditableInputFields.Single().IsDirty);
    }

    [TestMethod]
    public async Task ApplySelectedNodeDisplayNameDraftPatchesWorkflowDefinitionDraftJson()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "display_name": "Filter amount",
                  "config": {"field": "amount"}
                }
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual("Filter amount", viewModel.SelectedNodeDisplayNameDraft);
        Assert.IsFalse(viewModel.ApplySelectedNodeDisplayNameDraftCommand.CanExecute(null));

        viewModel.SelectedNodeDisplayNameDraft = "Filter total";

        Assert.IsTrue(viewModel.ApplySelectedNodeDisplayNameDraftCommand.CanExecute(null));

        viewModel.ApplySelectedNodeDisplayNameDraftCommand.Execute(null);

        using var draft = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        Assert.AreEqual(
            "Filter total",
            draft.RootElement
                .GetProperty("nodes")[0]
                .GetProperty("display_name")
                .GetString());
        Assert.AreEqual("Filter total", viewModel.SelectedWorkflowDefinitionNode?.DisplayName);
        Assert.AreEqual("Filter total", viewModel.SelectedNodeDisplayNameDraft);
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual(
            "Node display name applied to draft. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.ApplySelectedNodeDisplayNameDraftCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task ApplySelectedNodeConfigDraftPatchesWorkflowDefinitionDraftJson()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {"field": "amount"}
                }
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition(
                        "FilterRowsNode",
                        "Filter Rows",
                        schemaJson:
                            """
                            {
                              "type": "object",
                              "properties": {
                                "field": {"type": "string", "required": true}
                              }
                            }
                            """),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);
        viewModel.SelectedNodeConfigEditableInputFields.Single().InputValue = "total";

        Assert.IsTrue(viewModel.ApplySelectedNodeConfigDraftCommand.CanExecute(null));

        viewModel.ApplySelectedNodeConfigDraftCommand.Execute(null);

        using var document = JsonDocument.Parse(viewModel.WorkflowDefinitionDraftJson);
        Assert.AreEqual(
            "total",
            document.RootElement
                .GetProperty("nodes")[0]
                .GetProperty("config")
                .GetProperty("field")
                .GetString());
        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.AreEqual(
            "Node config applied to draft. Validate before saving.",
            viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionValidationError);
    }

    [TestMethod]
    public async Task ApplySelectedNodeConfigDraftRejectsInvalidFieldInput()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {"limit": 3}
                }
              ],
              "connections": []
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition(
                        "FilterRowsNode",
                        "Filter Rows",
                        schemaJson:
                            """
                            {
                              "type": "object",
                              "properties": {
                                "limit": {"type": "integer", "required": true}
                              }
                            }
                            """),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);
        var originalDraftJson = viewModel.WorkflowDefinitionDraftJson;
        viewModel.SelectedNodeConfigEditableInputFields.Single().InputValue = "abc";

        viewModel.ApplySelectedNodeConfigDraftCommand.Execute(null);

        Assert.AreEqual(originalDraftJson, viewModel.WorkflowDefinitionDraftJson);
        Assert.AreEqual(
            "Node config apply failed.",
            viewModel.WorkflowDefinitionValidationMessage);
        StringAssert.Contains(
            viewModel.WorkflowDefinitionValidationErrorMessage,
            "limit: EDITABLE_CONFIG_FIELD_INTEGER_INVALID");
    }

    [TestMethod]
    public async Task ApplySelectedNodeConfigDraftIsDisabledDuringRevisionConflict()
    {
        var definitionJson =
            """
            {
              "nodes": [
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {"field": "amount"}
                }
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition(
                        "FilterRowsNode",
                        "Filter Rows",
                        schemaJson:
                            """
                            {
                              "type": "object",
                              "properties": {
                                "field": {"type": "string"}
                              }
                            }
                            """),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        Assert.IsTrue(viewModel.ApplySelectedNodeConfigDraftCommand.CanExecute(null));

        viewModel.HasWorkflowDefinitionRevisionConflict = true;

        Assert.IsFalse(viewModel.ApplySelectedNodeConfigDraftCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task RefreshNodeDefinitionsShowsEmptyStateForEmptyCatalog()
    {
        var apiClient = new FakeApiClient
        {
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>()),
        };
        var viewModel = CreateViewModel(apiClient);

        Assert.IsTrue(viewModel.HasNodeDefinitionCatalogEmptyState);

        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        Assert.IsEmpty(viewModel.NodeDefinitions);
        Assert.IsFalse(viewModel.HasNodeDefinitions);
        Assert.IsTrue(viewModel.HasNodeDefinitionCatalogEmptyState);
        Assert.AreEqual("Loaded 0 node definition(s).", viewModel.NodeDefinitionCatalogMessage);
    }

    [TestMethod]
    public async Task RefreshNodeDefinitionsShowsErrorEnvelope()
    {
        var apiClient = new FakeApiClient
        {
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Failure(
                "NODE_DEFINITIONS_UNAVAILABLE",
                "Node registry unavailable."),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        Assert.IsEmpty(viewModel.NodeDefinitions);
        Assert.AreEqual("Node definition refresh failed.", viewModel.NodeDefinitionCatalogMessage);
        Assert.AreEqual(
            "NODE_DEFINITIONS_UNAVAILABLE: Node registry unavailable.",
            viewModel.NodeDefinitionCatalogErrorMessage);
        Assert.IsTrue(viewModel.HasNodeDefinitionCatalogError);
        Assert.IsFalse(viewModel.HasNodeDefinitions);
        Assert.IsTrue(viewModel.HasNodeDefinitionCatalogEmptyState);
    }

    [TestMethod]
    public void RefreshNodeDefinitionsIsDisabledWithoutToken()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        viewModel.Token = string.Empty;

        Assert.IsFalse(viewModel.CanUseEngineActions);
        Assert.IsFalse(viewModel.RefreshNodeDefinitionsCommand.CanExecute(null));
        Assert.AreEqual(
            "Action is disabled because EngineHost is not connected or authenticated.",
            viewModel.RefreshNodeDefinitionsDisabledReasonText);
    }

    [TestMethod]
    public void RefreshNodeDefinitionsDisabledReasonReflectsLoadingState()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        viewModel.IsLoadingNodeDefinitions = true;

        Assert.IsFalse(viewModel.RefreshNodeDefinitionsCommand.CanExecute(null));
        Assert.AreEqual(
            "Action is disabled because another operation is in progress.",
            viewModel.RefreshNodeDefinitionsDisabledReasonText);
    }

    [TestMethod]
    public void LoadSelectedWorkflowDefinitionIsDisabledWithoutSelection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.LoadSelectedWorkflowDefinitionCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task LoadSelectedWorkflowDefinitionIsDisabledWithoutToken()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        viewModel.Token = string.Empty;

        Assert.IsNotNull(viewModel.SelectedWorkflow);
        Assert.IsFalse(viewModel.LoadSelectedWorkflowDefinitionCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task SaveWorkflowDefinitionDraftIsEnabledOnlyWhenDirty()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 1)),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.IsFalse(viewModel.SaveWorkflowDefinitionDraftCommand.CanExecute(null));

        viewModel.WorkflowDefinitionDraftJson = """{"nodes":[],"connections":[]}""";

        Assert.IsTrue(viewModel.IsWorkflowDefinitionDraftDirty);
        Assert.IsTrue(viewModel.SaveWorkflowDefinitionDraftCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task StartSelectedWorkflowStoresRunFeedback()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
                new WorkflowRunDto
                {
                    WorkflowRunId = "run-1",
                    WorkflowId = "wf-1",
                    Status = "PENDING",
                }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "PENDING") }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.StartSelectedWorkflowCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", apiClient.StartedWorkflowId);
        Assert.AreEqual("run-1", viewModel.LastStartedRunId);
        Assert.AreEqual("PENDING", viewModel.LastStartedRunStatus);
        Assert.AreEqual("Started run run-1 (PENDING).", viewModel.WorkflowMessage);
        Assert.IsTrue(viewModel.HasLastStartedRun);
        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("wf-1", apiClient.LastRunWorkflowId);
    }

    [TestMethod]
    public async Task StartSelectedWorkflowRefreshesSelectedNodeDataPreviewWhenAvailable()
    {
        const string definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "generate",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {}
                }
              ],
              "connections": []
            }
            """;
        var workflow = Workflow("wf-1", "Daily Load", 1, definitionJson);
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { workflow }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(workflow),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
                Run("run-1", "wf-1", "SUCCEEDED")),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "SUCCEEDED") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto> { NodeRun("node-run-1", "run-1", "generate", "SUCCEEDED", 1, "done") }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto> { TableRef("table-1", "run-1", "node-run-1") }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":1,"amount":12.5}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.StartSelectedWorkflowCommand.ExecuteAsync(null);

        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("run-1", apiClient.LastNodeRunWorkflowRunId);
        Assert.AreEqual("run-1", apiClient.LastTableRefWorkflowRunId);
        Assert.AreEqual("table-1", apiClient.LastTableRowsTableRefId);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
    }

    [TestMethod]
    public async Task StartSelectedWorkflowWaitsForTerminalRunBeforeRefreshingPreview()
    {
        const string definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "generate",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {}
                }
              ],
              "connections": []
            }
            """;
        var workflow = Workflow("wf-1", "Daily Load", 1, definitionJson);
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { workflow }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(workflow),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
                Run("run-1", "wf-1", "PENDING")),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto> { NodeRun("node-run-1", "run-1", "generate", "SUCCEEDED", 1, "done") }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto> { TableRef("table-1", "run-1", "node-run-1") }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":3,"amount":30}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        apiClient.RunsResponses.Enqueue(
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }));
        apiClient.RunsResponses.Enqueue(
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "SUCCEEDED") }));
        var runRefreshDelayCount = 0;
        var viewModel = CreateViewModel(
            apiClient,
            dataPreviewRunRefreshDelay: _ =>
            {
                Assert.IsNull(
                    apiClient.LastTableRowsTableRefId,
                    "Full run preview should not refresh before the run reaches a terminal status.");
                runRefreshDelayCount++;
                return Task.CompletedTask;
            });

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.StartSelectedWorkflowCommand.ExecuteAsync(null);

        Assert.AreEqual(1, runRefreshDelayCount);
        Assert.AreEqual(2, apiClient.ListRunsCallCount);
        Assert.AreEqual("SUCCEEDED", viewModel.SelectedRun?.Status);
        Assert.AreEqual("table-1", apiClient.LastTableRowsTableRefId);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "3", "30" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
    }

    [TestMethod]
    public async Task StartSelectedWorkflowSelectsLastReadableOutputNodeAfterTerminalRun()
    {
        const string definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "generate",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {}
                },
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {}
                },
                {
                  "node_instance_id": "publish",
                  "node_type": "PublishSharedTablesNode",
                  "node_version": "1.0",
                  "config": {}
                }
              ],
              "connections": []
            }
            """;
        var workflow = Workflow("wf-1", "Daily Load", 1, definitionJson);
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { workflow }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(workflow),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
                Run("run-1", "wf-1", "PENDING")),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "SUCCEEDED") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-generate", "run-1", "generate", "SUCCEEDED", 1, "done"),
                    NodeRun("node-run-filter", "run-1", "filter", "SUCCEEDED", 1, "done"),
                    NodeRun("node-run-publish", "run-1", "publish", "SUCCEEDED", 1, "done"),
                }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-generate", "run-1", "node-run-generate"),
                    TableRef("table-filter", "run-1", "node-run-filter"),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-filter",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":4,"amount":40}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        Assert.AreEqual("generate", viewModel.SelectedWorkflowDefinitionNode?.NodeInstanceId);

        await viewModel.StartSelectedWorkflowCommand.ExecuteAsync(null);

        Assert.AreEqual("filter", viewModel.SelectedWorkflowDefinitionNode?.NodeInstanceId);
        Assert.AreEqual("table-filter", apiClient.LastTableRowsTableRefId);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "4", "40" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
    }

    [TestMethod]
    public async Task PreviewSelectedWorkflowNodeStartsPreviewRunAndLoadsDataPreview()
    {
        const string definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "generate",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {}
                }
              ],
              "connections": []
            }
            """;
        var workflow = Workflow("wf-1", "Daily Load", 1, definitionJson);
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { workflow }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(workflow),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
                Run("run-preview", "wf-1", "SUCCEEDED") with
                {
                    RunMode = "preview_to_node",
                    TargetNodeInstanceId = "generate",
                }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-preview", "wf-1", "SUCCEEDED") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto> { NodeRun("node-run-1", "run-preview", "generate", "SUCCEEDED", 1, "done") }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto> { TableRef("table-1", "run-preview", "node-run-1") }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":1,"amount":12.5}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsTrue(viewModel.PreviewSelectedWorkflowNodeCommand.CanExecute(null));

        await viewModel.PreviewSelectedWorkflowNodeCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", apiClient.StartedWorkflowId);
        Assert.AreEqual("preview_to_node", apiClient.StartedWorkflowRunMode);
        Assert.AreEqual("generate", apiClient.StartedTargetNodeInstanceId);
        Assert.AreEqual("run-preview", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("run-preview", apiClient.LastNodeRunWorkflowRunId);
        Assert.AreEqual("run-preview", apiClient.LastTableRefWorkflowRunId);
        Assert.AreEqual("table-1", apiClient.LastTableRowsTableRefId);
        Assert.AreEqual("run-preview", viewModel.LastStartedRunId);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
    }

    [TestMethod]
    public async Task PreviewSelectedWorkflowNodeRetriesUntilOutputTableIsReady()
    {
        const string definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "generate",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {}
                }
              ],
              "connections": []
            }
            """;
        var workflow = Workflow("wf-1", "Daily Load", 1, definitionJson);
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { workflow }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(workflow),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
                Run("run-preview", "wf-1", "PENDING") with
                {
                    RunMode = "preview_to_node",
                    TargetNodeInstanceId = "generate",
                }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-preview", "wf-1", "PENDING") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto> { NodeRun("node-run-old", "run-old", "generate", "SUCCEEDED", 1, "done") }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto> { TableRef("table-old", "run-old", "node-run-old") }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-old",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":99,"amount":990}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var previewTableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
            new List<TableRefDto> { TableRef("table-1", "run-preview", "node-run-1") });
        var previewTableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
            TableRows(
                "table-1",
                ["row_id", "amount"],
                [
                    JsonDocument.Parse("""{"row_id":2,"amount":20}""")
                        .RootElement
                        .Clone(),
                ],
                rowCount: 1));
        var previewRetryDelayCount = 0;
        var viewModel = CreateViewModel(
            apiClient,
            dataPreviewRunRefreshDelay: _ =>
            {
                previewRetryDelayCount++;
                return Task.CompletedTask;
            });

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-old", "wf-1", "SUCCEEDED"));
        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "99", "990" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());

        apiClient.NodeRunsResponses.Enqueue(
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>()));
        apiClient.NodeRunsResponses.Enqueue(
            ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto> { NodeRun("node-run-1", "run-preview", "generate", "SUCCEEDED", 1, "done") }));
        apiClient.TableRefsResponse = previewTableRefsResponse;
        apiClient.TableRowsResponse = previewTableRowsResponse;

        await viewModel.PreviewSelectedWorkflowNodeCommand.ExecuteAsync(null);

        Assert.AreEqual(3, apiClient.ListNodeRunsCallCount);
        Assert.AreEqual(1, previewRetryDelayCount);
        Assert.AreEqual("table-1", apiClient.LastTableRowsTableRefId);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "2", "20" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
    }

    [TestMethod]
    public async Task PreviewSelectedWorkflowNodeKeepsPreviousPreviewWhenStarted()
    {
        const string definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "generate",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {}
                }
              ],
              "connections": []
            }
            """;
        var workflow = Workflow("wf-1", "Daily Load", 1, definitionJson);
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { workflow }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(workflow),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>()),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Failure(
                "START_FAILED",
                "Preview start failed."),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto> { NodeRun("node-run-old", "run-old", "generate", "SUCCEEDED", 1, "done") }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto> { TableRef("table-old", "run-old", "node-run-old") }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-old",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":99,"amount":990}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-old", "wf-1", "SUCCEEDED"));
        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        await viewModel.PreviewSelectedWorkflowNodeCommand.ExecuteAsync(null);

        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "99", "990" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
        Assert.AreEqual("Selected node preview failed.", viewModel.DataPreviewMessage);
        Assert.AreEqual("START_FAILED: Preview start failed.", viewModel.DataPreviewErrorMessage);
    }

    [TestMethod]
    public void StartSelectedWorkflowIsDisabledWithoutSelection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.StartSelectedWorkflowCommand.CanExecute(null));
    }

    [TestMethod]
    public void StartSelectedWorkflowIsDisabledForInactiveWorkflow()
    {
        var viewModel = CreateViewModel(new FakeApiClient());
        viewModel.SelectedWorkflow = new WorkflowListItemViewModel(
            Workflow("wf-deleted", "Deleted Workflow", 1) with
            {
                Status = "DELETED",
            });

        Assert.IsFalse(viewModel.StartSelectedWorkflowCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task RefreshRunsLoadsRunsForSelectedWorkflow()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow("wf-1", "Daily Load", 1),
                    Workflow("wf-2", "Report", 2),
                }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto>
                {
                    Run("run-1", "wf-1", "RUNNING"),
                    Run("run-2", "wf-1", "SUCCEEDED"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.RefreshRunsCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", apiClient.LastRunWorkflowId);
        Assert.HasCount(2, viewModel.Runs);
        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("Loaded 2 run(s) for Daily Load.", viewModel.RunMessage);
        Assert.IsFalse(viewModel.HasRunError);
    }

    [TestMethod]
    public async Task CancelSelectedRunSendsRunIdAndRefreshesRuns()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }),
            CancelRunResponse = ApiResponseEnvelope<WorkflowProcessDto>.Success(
                new WorkflowProcessDto
                {
                    ProcessId = "proc-1",
                    WorkflowRunId = "run-1",
                    Status = "CANCEL_REQUESTED",
                    StartedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.RefreshRunsCommand.ExecuteAsync(null);
        apiClient.RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
            new List<WorkflowRunDto> { Run("run-1", "wf-1", "CANCEL_REQUESTED") });

        await viewModel.CancelSelectedRunCommand.ExecuteAsync(null);

        Assert.AreEqual("run-1", apiClient.CancelledWorkflowRunId);
        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("CANCEL_REQUESTED", viewModel.SelectedRun?.Status);
        Assert.IsFalse(viewModel.HasRunError);
    }

    [TestMethod]
    public void CancelSelectedRunIsDisabledWithoutSelection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.CancelSelectedRunCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task CancelSelectedRunIsEnabledOnlyForRunningRunWithToken()
    {
        var apiClient = new FakeApiClient
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshRunsCommand.ExecuteAsync(null);

        Assert.IsTrue(viewModel.CanUseCancelSelectedRunAction);
        Assert.IsTrue(viewModel.CancelSelectedRunCommand.CanExecute(null));
        Assert.IsNull(viewModel.CancelSelectedRunDisabledReasonText);
    }

    [TestMethod]
    public async Task CancelSelectedRunIsDisabledWhenTokenIsMissing()
    {
        var apiClient = new FakeApiClient
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshRunsCommand.ExecuteAsync(null);
        viewModel.Token = string.Empty;

        Assert.IsFalse(viewModel.CanUseCancelSelectedRunAction);
        Assert.IsFalse(viewModel.CancelSelectedRunCommand.CanExecute(null));
        Assert.AreEqual(
            "Action is disabled because EngineHost is not connected or authenticated.",
            viewModel.CancelSelectedRunDisabledReasonText);
    }

    [TestMethod]
    public async Task CancelSelectedRunIsDisabledForTerminalRun()
    {
        var apiClient = new FakeApiClient
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "SUCCEEDED") }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshRunsCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.CanUseCancelSelectedRunAction);
        Assert.IsFalse(viewModel.CancelSelectedRunCommand.CanExecute(null));
        Assert.AreEqual(
            "Action is disabled because the run has already reached a terminal state.",
            viewModel.CancelSelectedRunDisabledReasonText);
    }

    [TestMethod]
    public async Task CancelSelectedRunIsDisabledForPendingRun()
    {
        var apiClient = new FakeApiClient
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "PENDING") }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshRunsCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.CanUseCancelSelectedRunAction);
        Assert.IsFalse(viewModel.CancelSelectedRunCommand.CanExecute(null));
        Assert.AreEqual(
            "Action is disabled because the run is not currently running.",
            viewModel.CancelSelectedRunDisabledReasonText);
    }

    [TestMethod]
    public async Task RefreshNodeRunsLoadsProgressAndStageForSelectedRun()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "extract", "RUNNING", 0.5, "reading"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.RefreshRunsCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeRunsCommand.ExecuteAsync(null);

        Assert.AreEqual("run-1", apiClient.LastNodeRunWorkflowRunId);
        Assert.HasCount(1, viewModel.NodeRuns);
        Assert.AreEqual("extract", viewModel.NodeRuns[0].NodeInstanceId);
        Assert.AreEqual("50%", viewModel.NodeRuns[0].ProgressText);
        Assert.AreEqual("reading", viewModel.NodeRuns[0].CurrentStageText);
        Assert.AreEqual("Loaded 1 node run(s).", viewModel.NodeRunMessage);
        Assert.IsFalse(viewModel.HasNodeRunError);
    }

    private static MainWindowViewModel CreateViewModel(
        FakeApiClient apiClient,
        Func<CancellationToken, Task>? dataPreviewRunRefreshDelay = null)
    {
        return new MainWindowViewModel(
            new EngineHostHealthClient(apiClient),
            apiClient,
            new EngineHostRuntimeEventStreamClient(),
            dataPreviewRunRefreshDelay: dataPreviewRunRefreshDelay)
        {
            BaseUrl = "http://127.0.0.1:8000",
            Token = "secret",
            ConnectionStatus = ConnectionStatus.Connected,
        };
    }

    private static WorkflowDefinitionDto Workflow(
        string workflowId,
        string name,
        int version,
        string definitionJson = """{"nodes":[]}""")
    {
        return new WorkflowDefinitionDto
        {
            WorkflowId = workflowId,
            Name = name,
            RevisionId = $"rev-{workflowId}",
            Version = version,
            DefinitionHash = $"hash-{workflowId}",
            Status = "ACTIVE",
            UpdatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            Definition = JsonDocument.Parse(definitionJson).RootElement.Clone(),
        };
    }

    private static WorkflowRevisionDto Revision(
        string revisionId,
        string workflowId,
        int version,
        string definitionJson)
    {
        return new WorkflowRevisionDto
        {
            RevisionId = revisionId,
            WorkflowId = workflowId,
            Version = version,
            DefinitionHash = $"hash-{workflowId}-{version}",
            Definition = JsonDocument.Parse(definitionJson).RootElement.Clone(),
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            CreatedBy = "tester",
        };
    }

    private static WorkflowRunDto Run(string workflowRunId, string workflowId, string status)
    {
        return new WorkflowRunDto
        {
            WorkflowRunId = workflowRunId,
            WorkflowId = workflowId,
            WorkflowVersion = 1,
            Status = status,
            StateVersion = 1,
            StartedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
        };
    }

    private static NodeRunDto NodeRun(
        string nodeRunId,
        string workflowRunId,
        string nodeInstanceId,
        string status,
        double? progress,
        string? currentStage)
    {
        return new NodeRunDto
        {
            NodeRunId = nodeRunId,
            WorkflowRunId = workflowRunId,
            NodeInstanceId = nodeInstanceId,
            NodeType = "builtin.table",
            Status = status,
            StateVersion = 1,
            Progress = progress,
            CurrentStage = currentStage,
            Attempt = 1,
            LastHeartbeat = DateTimeOffset.Parse("2026-06-29T01:03:03Z"),
        };
    }

    private static TableRefDto TableRef(
        string tableRefId,
        string workflowRunId,
        string nodeRunId)
    {
        return new TableRefDto
        {
            TableRefId = tableRefId,
            WorkflowRunId = workflowRunId,
            NodeRunId = nodeRunId,
            Role = "OUTPUT",
            StorageKind = "RUNTIME_SQL",
            Scope = "WORKFLOW_SCOPE",
            Mutability = "IMMUTABLE",
            ProviderId = "runtime",
            LogicalTableId = "orders",
            Schema = JsonDocument.Parse("""{"fields":[]}""").RootElement.Clone(),
            SchemaFingerprint = "schema-1",
            Version = 1,
            Capabilities = ["READ"],
            LifecycleStatus = "PUBLISHED",
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
        };
    }

    private static TableDataRowsDto TableRows(
        string tableRefId,
        string[] columns,
        JsonElement[] rows,
        long rowCount)
    {
        return new TableDataRowsDto
        {
            TableRefId = tableRefId,
            Offset = 0,
            Limit = 50,
            RowCount = rowCount,
            Columns = columns,
            Rows = rows,
            HasMore = false,
        };
    }

    private static NodeDefinitionDto NodeDefinition(
        string nodeType,
        string displayName,
        string? inputPort = null,
        string? outputPort = null,
        string? schemaJson = null)
    {
        return new NodeDefinitionDto
        {
            NodeType = nodeType,
            NodeVersion = "1.0",
            DisplayName = displayName,
            InputPorts = inputPort is null
                ? []
                : [new NodePortDefinitionDto { Name = inputPort, Required = true }],
            OutputPorts = outputPort is null
                ? []
                : [new NodePortDefinitionDto { Name = outputPort, Required = false }],
            ExecutionMode = "PROCESS_POOL",
            DefaultTimeoutSeconds = 60,
            RetrySafe = false,
            UiVisibility = "visible",
            ConfigSchemaVersion = schemaJson is null ? string.Empty : "1.0",
            ConfigSchema = schemaJson is null
                ? null
                : JsonDocument.Parse(schemaJson).RootElement.Clone(),
        };
    }

    private sealed class FakeApiClient : IEngineHostApiClient
    {
        public ApiResponseEnvelope<List<NodeDefinitionDto>> NodeDefinitionsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(new List<NodeDefinitionDto>());

        public ApiResponseEnvelope<List<WorkflowDefinitionDto>> WorkflowsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(new List<WorkflowDefinitionDto>());

        public ApiResponseEnvelope<WorkflowDefinitionDto> WorkflowDetailResponse { get; set; } =
            ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "NOT_CONFIGURED",
                "No workflow detail response configured.");

        public ApiResponseEnvelope<WorkflowDefinitionDto> CreateWorkflowResponse { get; set; } =
            ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "NOT_CONFIGURED",
                "No create response configured.");

        public ApiResponseEnvelope<WorkflowValidationResultDto> ValidateWorkflowDraftResponse { get; set; } =
            ApiResponseEnvelope<WorkflowValidationResultDto>.Failure(
                "NOT_CONFIGURED",
                "No validate response configured.");

        public ApiResponseEnvelope<WorkflowDefinitionDto> UpdateWorkflowResponse { get; set; } =
            ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "NOT_CONFIGURED",
                "No update response configured.");

        public ApiResponseEnvelope<List<WorkflowRevisionDto>> WorkflowRevisionsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(new List<WorkflowRevisionDto>());

        public ApiResponseEnvelope<WorkflowRunDto> StartWorkflowResponse { get; set; } =
            ApiResponseEnvelope<WorkflowRunDto>.Failure("NOT_CONFIGURED", "No run response configured.");

        public ApiResponseEnvelope<List<WorkflowRunDto>> RunsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(new List<WorkflowRunDto>());

        public Queue<ApiResponseEnvelope<List<WorkflowRunDto>>> RunsResponses { get; } = new();

        public ApiResponseEnvelope<List<NodeRunDto>> NodeRunsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>());

        public Queue<ApiResponseEnvelope<List<NodeRunDto>>> NodeRunsResponses { get; } = new();

        public ApiResponseEnvelope<WorkflowProcessDto> CancelRunResponse { get; set; } =
            ApiResponseEnvelope<WorkflowProcessDto>.Failure("NOT_CONFIGURED", "No cancel response configured.");

        public ApiResponseEnvelope<List<TableRefDto>> TableRefsResponse { get; set; } =
            ApiResponseEnvelope<List<TableRefDto>>.Success(new List<TableRefDto>());

        public ApiResponseEnvelope<TableDataRowsDto> TableRowsResponse { get; set; } =
            ApiResponseEnvelope<TableDataRowsDto>.Success(
                new TableDataRowsDto
                {
                    TableRefId = "table-1",
                    Offset = 0,
                    Limit = 50,
                    RowCount = 0,
                    Columns = [],
                    Rows = [],
                    HasMore = false,
                });

        public EngineHostConnectionSettings? LastSettings { get; private set; }

        public string? LastWorkflowDetailId { get; private set; }

        public string? CreatedWorkflowName { get; private set; }

        public JsonElement? CreatedWorkflowDefinition { get; private set; }

        public JsonElement? ValidatedWorkflowDraftDefinition { get; private set; }

        public string? UpdatedWorkflowId { get; private set; }

        public string? UpdatedWorkflowName { get; private set; }

        public JsonElement? UpdatedWorkflowDefinition { get; private set; }

        public string? UpdatedWorkflowBaseRevisionId { get; private set; }

        public string? LastWorkflowRevisionsWorkflowId { get; private set; }

        public string? StartedWorkflowId { get; private set; }

        public string? StartedWorkflowRunMode { get; private set; }

        public string? StartedTargetNodeInstanceId { get; private set; }

        public string? LastRunWorkflowId { get; private set; }

        public int ListRunsCallCount { get; private set; }

        public string? LastNodeRunWorkflowRunId { get; private set; }

        public int ListNodeRunsCallCount { get; private set; }

        public string? LastTableRefWorkflowRunId { get; private set; }

        public string? LastTableRowsTableRefId { get; private set; }

        public string? CancelledWorkflowRunId { get; private set; }

        public Task<ApiResponseEnvelope<HealthStatusDto>> GetHealthAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }));
        }

        public Task<ApiResponseEnvelope<List<NodeDefinitionDto>>> ListNodeDefinitionsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            return Task.FromResult(NodeDefinitionsResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowDefinitionDto>>> ListWorkflowsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            return Task.FromResult(WorkflowsResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> CreateWorkflowAsync(
            EngineHostConnectionSettings settings,
            string name,
            JsonElement definition,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            CreatedWorkflowName = name;
            CreatedWorkflowDefinition = definition.Clone();
            return Task.FromResult(CreateWorkflowResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowValidationResultDto>> ValidateWorkflowDraftAsync(
            EngineHostConnectionSettings settings,
            JsonElement definition,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            ValidatedWorkflowDraftDefinition = definition.Clone();
            return Task.FromResult(ValidateWorkflowDraftResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> UpdateWorkflowAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            string? name,
            JsonElement definition,
            string baseRevisionId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            UpdatedWorkflowId = workflowId;
            UpdatedWorkflowName = name;
            UpdatedWorkflowDefinition = definition.Clone();
            UpdatedWorkflowBaseRevisionId = baseRevisionId;
            return Task.FromResult(UpdateWorkflowResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> GetWorkflowAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastWorkflowDetailId = workflowId;
            return Task.FromResult(WorkflowDetailResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowRevisionDto>>> ListWorkflowRevisionsAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastWorkflowRevisionsWorkflowId = workflowId;
            return Task.FromResult(WorkflowRevisionsResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowRevisionDto>> GetWorkflowRevisionAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            string revisionId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            StartedWorkflowId = workflowId;
            StartedWorkflowRunMode = "full";
            StartedTargetNodeInstanceId = null;
            return Task.FromResult(StartWorkflowResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            string runMode,
            string? targetNodeInstanceId = null,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            StartedWorkflowId = workflowId;
            StartedWorkflowRunMode = runMode;
            StartedTargetNodeInstanceId = targetNodeInstanceId;
            return Task.FromResult(StartWorkflowResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
            EngineHostConnectionSettings settings,
            string? workflowId = null,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastRunWorkflowId = workflowId;
            ListRunsCallCount++;
            return Task.FromResult(
                RunsResponses.Count > 0
                    ? RunsResponses.Dequeue()
                    : RunsResponse);
        }

        public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastNodeRunWorkflowRunId = workflowRunId;
            ListNodeRunsCallCount++;
            return Task.FromResult(
                NodeRunsResponses.Count > 0
                    ? NodeRunsResponses.Dequeue()
                    : NodeRunsResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelRunAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            CancelledWorkflowRunId = workflowRunId;
            return Task.FromResult(CancelRunResponse);
        }

        public Task<ApiResponseEnvelope<List<TableRefDto>>> ListTableRefsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastTableRefWorkflowRunId = workflowRunId;
            return Task.FromResult(TableRefsResponse);
        }

        public Task<ApiResponseEnvelope<TableDataRowsDto>> GetTableDataRowsAsync(
            EngineHostConnectionSettings settings,
            string tableRefId,
            int offset = 0,
            int limit = 50,
            IReadOnlyCollection<string>? columns = null,
            IReadOnlyCollection<string>? orderBy = null,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastTableRowsTableRefId = tableRefId;
            return Task.FromResult(TableRowsResponse);
        }

        public Task<ApiResponseEnvelope<List<RuntimeEventDto>>> ListEventsAsync(
            EngineHostConnectionSettings settings,
            long? afterSequenceNumber = null,
            string? workflowRunId = null,
            string? nodeRunId = null,
            string? eventType = null,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<AuditEventDto>>> ListAuditEventsAsync(
            EngineHostConnectionSettings settings,
            string? workflowRunId = null,
            string? nodeRunId = null,
            string? eventType = null,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationsAsync(
            EngineHostConnectionSettings settings,
            string? shareName = null,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationVersionsAsync(
            EngineHostConnectionSettings settings,
            string shareName,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }
    }
}
