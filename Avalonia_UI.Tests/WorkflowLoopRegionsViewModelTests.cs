using System.Collections.Generic;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowLoopRegionsViewModelTests
{
    [TestMethod]
    public async Task SelectingRegionLoadsEditorWithoutApplyingUntilCommand()
    {
        string? appliedJson = null;
        var viewModel = new WorkflowLoopRegionsViewModel(
            key => key,
            json =>
            {
                appliedJson = json;
                return Task.CompletedTask;
            });
        var readResult = WorkflowLoopRegionDraftReader.Read(WorkflowJson);
        viewModel.Load(WorkflowJson, readResult, Nodes());

        Assert.HasCount(1, viewModel.Regions);
        Assert.IsNull(appliedJson);

        viewModel.SelectedRegion = viewModel.Regions[0];

        Assert.AreEqual("orders_loop", viewModel.LoopIdDraft);
        Assert.AreEqual("start", viewModel.SelectedStartNode?.NodeInstanceId);
        Assert.AreEqual("judge", viewModel.SelectedJudgeNode?.NodeInstanceId);
        Assert.IsTrue(viewModel.BodyNodeOptions[1].IsBodySelected);
        Assert.IsNull(appliedJson);

        viewModel.MaxIterationsDraft = 9;
        await viewModel.ApplyDraftCommand.ExecuteAsync(null);

        Assert.IsNotNull(appliedJson);
        var updated = WorkflowLoopRegionDraftReader.Read(appliedJson!);
        Assert.IsTrue(updated.Succeeded);
        Assert.AreEqual(9, updated.Regions[0].MaxIterations);
    }

    private const string WorkflowJson =
        """
        {
          "nodes": [
            {"node_instance_id":"start","config":{"loop_id":"orders_loop"}},
            {"node_instance_id":"body","config":{}},
            {"node_instance_id":"judge","config":{"loop_id":"orders_loop"}}
          ],
          "connections": [],
          "control_protocol": {
            "mode":"preview",
            "loop_regions":[{
              "loop_id":"orders_loop",
              "start_node_id":"start",
              "judge_node_id":"judge",
              "body_node_ids":["body"],
              "max_iterations":3
            }]
          }
        }
        """;

    private static IReadOnlyList<WorkflowDefinitionDraftNode> Nodes()
    {
        return
        [
            new WorkflowDefinitionDraftNode { NodeInstanceId = "start", NodeTypeDisplayName = "Loop Start" },
            new WorkflowDefinitionDraftNode { NodeInstanceId = "body", NodeTypeDisplayName = "Body" },
            new WorkflowDefinitionDraftNode { NodeInstanceId = "judge", NodeTypeDisplayName = "Loop Judge" },
        ];
    }
}
