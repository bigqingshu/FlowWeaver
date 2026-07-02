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
        Assert.AreEqual(1, viewModel.WorkflowDefinitionDraftConnectionCount);
        Assert.IsNotNull(viewModel.WorkflowDefinitionDraftStructure);
        Assert.AreEqual(
            "source",
            viewModel.WorkflowDefinitionDraftStructure.Nodes[0].NodeInstanceId);
        Assert.AreEqual(
            "c1",
            viewModel.WorkflowDefinitionDraftStructure.Connections[0].ConnectionId);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionDraftStructureWarnings);
        Assert.AreSame(detail.Nodes[0], viewModel.SelectedWorkflowDefinitionNode);
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
    public async Task ChangingWorkflowClearsSelectedWorkflowDefinitionNode()
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

        viewModel.SelectedWorkflow = viewModel.Workflows[1];

        Assert.IsNull(viewModel.WorkflowDefinitionDetail);
        Assert.IsNull(viewModel.SelectedWorkflowDefinitionNode);
        Assert.IsNull(viewModel.SelectedNodeConfigDraft);
        Assert.IsNull(viewModel.SelectedNodeConfigEditableDraft);
        Assert.IsFalse(viewModel.HasSelectedNodeConfigEditableInputFields);
        Assert.IsEmpty(viewModel.SelectedNodeConfigEditableInputFields);
        Assert.AreEqual(string.Empty, viewModel.WorkflowDefinitionDraftJson);
        Assert.IsNull(viewModel.WorkflowDefinitionDraftStructure);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionDraftStructure);
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

        Assert.IsTrue(viewModel.HasWorkflowDefinitionRevisionConflict);
        Assert.IsFalse(viewModel.SaveWorkflowDefinitionDraftCommand.CanExecute(null));
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

    private static MainWindowViewModel CreateViewModel(FakeApiClient apiClient)
    {
        return new MainWindowViewModel(
            new EngineHostHealthClient(apiClient),
            apiClient)
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

        public ApiResponseEnvelope<List<NodeRunDto>> NodeRunsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>());

        public ApiResponseEnvelope<WorkflowProcessDto> CancelRunResponse { get; set; } =
            ApiResponseEnvelope<WorkflowProcessDto>.Failure("NOT_CONFIGURED", "No cancel response configured.");

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

        public string? LastRunWorkflowId { get; private set; }

        public string? LastNodeRunWorkflowRunId { get; private set; }

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
            return Task.FromResult(RunsResponse);
        }

        public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastNodeRunWorkflowRunId = workflowRunId;
            return Task.FromResult(NodeRunsResponse);
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
            throw new NotSupportedException();
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
