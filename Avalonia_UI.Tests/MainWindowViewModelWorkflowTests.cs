using System;
using System.Collections.Generic;
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
        Assert.AreEqual("GenerateTestTableNode@1.0", detail.Nodes[0].TypeText);
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

    private sealed class FakeApiClient : IEngineHostApiClient
    {
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
            throw new NotSupportedException();
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
