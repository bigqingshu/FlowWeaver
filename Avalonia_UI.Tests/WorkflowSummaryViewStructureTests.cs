using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowSummaryViewStructureTests
{
    [TestMethod]
    public void NodeTemplateShowsCompactNodeSummaryWithoutConfigJson()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowNodesSectionText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDraftNodeCountText}\"");
        StringAssert.Contains(
            xaml,
            "IsChecked=\"{Binding IsBatchSelected, Mode=TwoWay}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding WorkflowDefinitionDraftNodes}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedWorkflowDefinitionNode}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding OrderText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TitleText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding EnabledText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeSummaryText}\"");
        Assert.IsFalse(xaml.Contains("Text=\"{Binding NodeEditorStatusText}\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("Text=\"{Binding ConfigJson}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            xaml.Contains("Text=\"{Binding WorkflowDefinitionBatchSelectedNodeCountText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            xaml.Contains("Text=\"{Binding WorkflowLinearChainStatusText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            xaml.Contains("Text=\"{Binding WorkflowDefinitionValidationMessage}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            xaml.Contains("Text=\"{Binding WorkflowDefinitionValidationErrorMessage}\"", StringComparison.Ordinal));
        StringAssert.Contains(xaml, "RowDefinitions=\"Auto,Auto\"");
        Assert.IsFalse(xaml.Contains("NodeEditorStatusText}\" Command=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowSummaryViewDoesNotOwnNodeSelectionList()
    {
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");
        var configXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSelectedNodeConfigView.axaml");

        StringAssert.Contains(summaryXaml, "<workflow:WorkflowSelectedNodeConfigView />");
        StringAssert.Contains(configXaml, "Text=\"{Binding SelectedNodeConfigDraftSummaryText}\"");
        StringAssert.Contains(configXaml, "IsVisible=\"{Binding HasSelectedWorkflowDefinitionNode}\"");
        StringAssert.Contains(configXaml, "Text=\"{Binding NodeInstanceIdText}\"");
        StringAssert.Contains(configXaml, "Text=\"{Binding SelectedWorkflowDefinitionNode.NodeInstanceId}\"");
        StringAssert.Contains(configXaml, "Text=\"{Binding NodeTypeText}\"");
        StringAssert.Contains(configXaml, "Text=\"{Binding SelectedWorkflowDefinitionNode.NodeType}\"");
        StringAssert.Contains(configXaml, "Text=\"{Binding NodeVersionText}\"");
        StringAssert.Contains(configXaml, "Text=\"{Binding SelectedWorkflowDefinitionNode.NodeVersion}\"");
        StringAssert.Contains(configXaml, "Text=\"{Binding DisplayNameText}\"");
        StringAssert.Contains(configXaml, "Text=\"{Binding SelectedNodeDisplayNameDraft, Mode=TwoWay");
        StringAssert.Contains(configXaml, "Content=\"{Binding ApplyNodeDisplayNameText}\"");
        StringAssert.Contains(configXaml, "Command=\"{Binding ApplySelectedNodeDisplayNameDraftCommand}\"");
        StringAssert.Contains(
            configXaml,
            "ItemsSource=\"{Binding SelectedNodeConfigEditableInputFields}\"");
        Assert.IsFalse(
            configXaml.Contains("Text=\"{Binding SelectedWorkflowDefinitionNode.NodeInstanceId, Mode=TwoWay", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("ItemsSource=\"{Binding WorkflowDefinitionDetail.Nodes}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("SelectedItem=\"{Binding SelectedWorkflowDefinitionNode}\"", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeTemplateDoesNotIntroduceNodeEditingActions()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        Assert.IsFalse(xaml.Contains("EditNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ConfigureNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("OpenNodeEditor", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("SaveNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ListNodeDefinitionsAsync", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeConfigEditorBindsToInputFieldsAndApplyCommand()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSelectedNodeConfigView.axaml");

        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding SelectedNodeConfigEditableInputFields}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding ApplySelectedNodeConfigDraftCommand}\"");
        StringAssert.Contains(
            xaml,
            "x:DataType=\"vm:NodeConfigEditableFieldInputViewModel\"");
        StringAssert.Contains(xaml, "Text=\"{Binding InputValue, Mode=TwoWay");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding InputValue, Mode=TwoWay}\"");
    }

    [TestMethod]
    public void NodeConfigEditorUsesViewHelperBindingsWithoutConverters()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSelectedNodeConfigView.axaml");

        StringAssert.Contains(
            xaml,
            "IsVisible=\"{Binding HasSelectedNodeConfigEditableInputFields}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DisplayLabel}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TypeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding RequiredText}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsTextInput}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsEnumInput}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsBooleanInput}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding BooleanValues}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WarningText}\"");
        Assert.IsFalse(xaml.Contains("Converter=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void StructuredEditFormsBindToDraftInputsAndCommands()
    {
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");
        var addNodeXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowAddNodeView.axaml");
        var nodeListXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");

        StringAssert.Contains(
            summaryXaml,
            "<workflow:WorkflowAddNodeView IsVisible=\"{Binding IsWorkflowAddNodePanelVisible}\"/>");
        StringAssert.Contains(
            summaryXaml,
            "Command=\"{Binding OpenWorkflowAddNodePanelCommand}\"");
        Assert.IsFalse(
            nodeListXaml.Contains("<workflow:WorkflowAddNodeView", StringComparison.Ordinal));
        Assert.IsFalse(
            nodeListXaml.Contains("Command=\"{Binding OpenWorkflowAddNodePanelCommand}\"", StringComparison.Ordinal));
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding AddNodeText}\"");
        StringAssert.Contains(addNodeXaml, "Content=\"{Binding CloseText}\"");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding CloseWorkflowAddNodePanelCommand}\"");
        StringAssert.Contains(addNodeXaml, "Content=\"{Binding AddNodeText}\"");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(nodeListXaml, "Content=\"{Binding DeleteNodeText}\"");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NodeTypeText}\"");
        StringAssert.Contains(
            addNodeXaml,
            "ItemsSource=\"{Binding NodeDefinitions}\"");
        StringAssert.Contains(
            addNodeXaml,
            "SelectedItem=\"{Binding SelectedNewDraftNodeDefinition, Mode=TwoWay}\"");
        StringAssert.Contains(
            addNodeXaml,
            "ToolTip.Tip=\"{Binding RefreshNodeDefinitionsDisabledReasonText}\"");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding RefreshNodeDefinitionsCommand}\"");
        StringAssert.Contains(
            addNodeXaml,
            "x:DataType=\"vm:NodeDefinitionListItemViewModel\"");
        Assert.IsFalse(
            addNodeXaml.Contains("Text=\"{Binding NodeInstanceIdText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            addNodeXaml.Contains("Text=\"{Binding NodeVersionText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            addNodeXaml.Contains("Text=\"{Binding ConfigJsonText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            addNodeXaml.Contains("Text=\"{Binding NewDraftNodeInstanceId, Mode=TwoWay", StringComparison.Ordinal));
        Assert.IsFalse(
            addNodeXaml.Contains("Text=\"{Binding NewDraftNodeType, Mode=TwoWay", StringComparison.Ordinal));
        Assert.IsFalse(
            addNodeXaml.Contains("Text=\"{Binding NewDraftNodeVersion, Mode=TwoWay", StringComparison.Ordinal));
        Assert.IsFalse(
            addNodeXaml.Contains("Text=\"{Binding NewDraftNodeDisplayName, Mode=TwoWay", StringComparison.Ordinal));
        Assert.IsFalse(
            addNodeXaml.Contains("Text=\"{Binding NewDraftNodeConfigJson, Mode=TwoWay", StringComparison.Ordinal));
        StringAssert.Contains(
            nodeListXaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftNodeCommand}\"");
        Assert.IsFalse(
            addNodeXaml.Contains(
                "Text=\"{Binding SelectedWorkflowDefinitionDraftNodeInstanceId, Mode=TwoWay",
                StringComparison.Ordinal));

        StringAssert.Contains(
            summaryXaml,
            "Text=\"{Binding WorkflowDefinitionDraftConnectionCountText}\"");
        StringAssert.Contains(
            summaryXaml,
            "ItemsSource=\"{Binding WorkflowDefinitionDraftStructure.Connections}\"");
        StringAssert.Contains(
            summaryXaml,
            "x:DataType=\"models:WorkflowDefinitionDraftConnection\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding ConnectionId}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding SourceNodeId}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding SourcePort}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding TargetNodeId}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding TargetPort}\"");
        Assert.IsFalse(
            summaryXaml.Contains("Command=\"{Binding AddWorkflowDefinitionDraftConnectionCommand}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("Command=\"{Binding DeleteWorkflowDefinitionDraftConnectionCommand}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("Text=\"{Binding NewDraftConnectionId, Mode=TwoWay", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("NewDraftConnectionSourceNodeId", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("NewDraftConnectionSourcePort", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("NewDraftConnectionTargetNodeId", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("NewDraftConnectionTargetPort", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("SelectedNewDraftConnectionSourceNode", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("SelectedNewDraftConnectionTargetNode", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("SelectedWorkflowDefinitionDraftConnectionId", StringComparison.Ordinal));
        StringAssert.Contains(
            summaryXaml,
            "Content=\"{Binding ShowConnectionsText}\"");
        Assert.IsFalse(summaryXaml.Contains("Converter=", StringComparison.Ordinal));
        Assert.IsFalse(addNodeXaml.Contains("Converter=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowDefinitionCardOmitsRevisionHistoryList()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.RevisionId}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.DefinitionHash}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.UpdatedAtText}\"");
        Assert.IsFalse(xaml.Contains("WorkflowDefinitionDetail.Revisions", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("WorkflowRevisionListItemViewModel", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("SelectedRevision", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowPageKeepsDefinitionWorkspaceWithDedicatedNodeListColumn()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Pages",
            "WorkflowPage.axaml");

        StringAssert.Contains(xaml, "ColumnDefinitions=\"340,*,340\"");
        StringAssert.Contains(xaml, "RowDefinitions=\"*,Auto\"");
        StringAssert.Contains(xaml, "RowSpacing=\"16\"");
        StringAssert.Contains(xaml, "<workflow:WorkflowListView Grid.Column=\"0\"");
        StringAssert.Contains(xaml, "Grid.RowSpan=\"2\"");
        StringAssert.Contains(xaml, "<workflow:WorkflowSummaryView Grid.Column=\"1\" />");
        StringAssert.Contains(xaml, "<workflow:WorkflowNodeListView Grid.Column=\"2\" />");
        StringAssert.Contains(xaml, "<workflow:WorkflowDataPreviewView Grid.Row=\"1\"");
        StringAssert.Contains(xaml, "Grid.Column=\"1\"");
        StringAssert.Contains(xaml, "Grid.ColumnSpan=\"2\"");
        Assert.IsFalse(xaml.Contains("<workflow:WorkflowEditorView", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("<workflow:WorkflowNodeCatalogView", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeActionGroupContainsDraftMutationButtonsAndAdvancedToggle()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");
        var addNodeXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowAddNodeView.axaml");
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding NodeActionsSectionText}\"");
        StringAssert.Contains(xaml, "Content=\"?\"");
        StringAssert.Contains(xaml, "ToolTip.Tip=\"{Binding NodeMoveSemanticsText}\"");
        StringAssert.Contains(xaml, "<Button.Flyout>");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeMoveSemanticsText}\"");
        StringAssert.Contains(xaml, "<WrapPanel Orientation=\"Horizontal\"");
        Assert.AreEqual(
            1,
            CountOccurrences(xaml, "Text=\"{Binding NodeMoveSemanticsText}\""),
            "The node move semantics text should live only in the info flyout.");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(
            summaryXaml,
            "Command=\"{Binding OpenWorkflowAddNodePanelCommand}\"");
        StringAssert.Contains(
            summaryXaml,
            "<workflow:WorkflowAddNodeView IsVisible=\"{Binding IsWorkflowAddNodePanelVisible}\"/>");
        Assert.IsFalse(
            xaml.Contains("Content=\"{Binding AddNodeText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            xaml.Contains("Command=\"{Binding OpenWorkflowAddNodePanelCommand}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            xaml.Contains("IsWorkflowAddNodePanelVisible", StringComparison.Ordinal));
        StringAssert.Contains(xaml, "Content=\"{Binding MoveNodeUpText}\"");
        StringAssert.Contains(
            xaml,
            "ToolTip.Tip=\"{Binding MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding MoveSelectedWorkflowDefinitionDraftNodeUpCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding MoveNodeDownText}\"");
        StringAssert.Contains(
            xaml,
            "ToolTip.Tip=\"{Binding MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding MoveSelectedWorkflowDefinitionDraftNodeDownCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding CopyNodeText}\"");
        StringAssert.Contains(
            xaml,
            "ToolTip.Tip=\"{Binding CopyWorkflowDefinitionDraftNodeDisabledReasonText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding CopyWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding DeleteNodeText}\"");
        StringAssert.Contains(
            xaml,
            "ToolTip.Tip=\"{Binding DeleteWorkflowDefinitionDraftNodeDisabledReasonText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding DeleteSelectedNodesText}\"");
        StringAssert.Contains(
            xaml,
            "ToolTip.Tip=\"{Binding DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding DeleteSelectedWorkflowDefinitionDraftNodesCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding ShowAdvancedDraftJsonText}\"");
        StringAssert.Contains(
            xaml,
            "IsChecked=\"{Binding IsWorkflowDraftJsonAdvancedVisible, Mode=TwoWay}\"");
        StringAssert.Contains(
            summaryXaml,
            "<workflow:WorkflowEditorView IsVisible=\"{Binding IsWorkflowDraftJsonAdvancedVisible}\"");
        Assert.IsFalse(
            summaryXaml.Contains("Text=\"{Binding NodeActionsSectionText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("Content=\"{Binding ShowAdvancedDraftJsonText}\"", StringComparison.Ordinal));

        var actionGroupIndex = xaml.IndexOf(
            "Text=\"{Binding NodeActionsSectionText}\"",
            StringComparison.Ordinal);
        var advancedToggleIndex = xaml.IndexOf(
            "Content=\"{Binding ShowAdvancedDraftJsonText}\"",
            StringComparison.Ordinal);
        var editorIndex = summaryXaml.IndexOf(
            "<workflow:WorkflowEditorView IsVisible=\"{Binding IsWorkflowDraftJsonAdvancedVisible}\"",
            StringComparison.Ordinal);
        Assert.IsTrue(
            actionGroupIndex >= 0 && advancedToggleIndex > actionGroupIndex,
            "The draft JSON toggle should live inside the node action group.");
        Assert.IsGreaterThanOrEqualTo(
            0,
            editorIndex,
            "The draft JSON editor should remain controlled by the node action group's advanced toggle.");

        var infoFlyoutIndex = xaml.IndexOf("<Button.Flyout>", StringComparison.Ordinal);
        var nodeMoveSemanticsIndex = xaml.IndexOf(
            "Text=\"{Binding NodeMoveSemanticsText}\"",
            StringComparison.Ordinal);
        var actionButtonsIndex = xaml.IndexOf(
            "<WrapPanel Orientation=\"Horizontal\"",
            StringComparison.Ordinal);
        Assert.IsTrue(
            infoFlyoutIndex >= 0 && nodeMoveSemanticsIndex > infoFlyoutIndex,
            "The node move semantics explanation should be hidden behind the info button.");
        Assert.IsGreaterThan(
            nodeMoveSemanticsIndex,
            actionButtonsIndex,
            "The node action buttons should stay below the compact info flyout without permanent log text.");
    }

    [TestMethod]
    public void WorkflowDataPreviewViewHostsReadOnlyDataPreview()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowDataPreviewView.axaml");
        var nodeListXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding DataPreviewSectionText}\"");
        StringAssert.Contains(xaml, "Content=\"?\"");
        StringAssert.Contains(xaml, "ToolTip.Tip=\"{Binding DataPreviewPendingText}\"");
        StringAssert.Contains(xaml, "<Button.Flyout>");
        StringAssert.Contains(xaml, "Text=\"{Binding DataPreviewPendingText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowRunGuardText}\"");
        Assert.AreEqual(
            1,
            CountOccurrences(xaml, "Text=\"{Binding DataPreviewPendingText}\""),
            "The data preview guidance should live only in the info flyout.");
        Assert.AreEqual(
            1,
            CountOccurrences(xaml, "Text=\"{Binding WorkflowRunGuardText}\""),
            "The workflow run guard explanation should live only in the info flyout.");
        Assert.IsFalse(
            xaml.Contains("Text=\"{Binding DataPreviewEmptyText}\"", StringComparison.Ordinal),
            "The data preview empty guidance should not occupy a permanent line.");
        Assert.IsFalse(
            xaml.Contains("Text=\"{Binding DataPreviewSourceText}\"", StringComparison.Ordinal),
            "The data preview source should move out of the permanent text row.");
        StringAssert.Contains(xaml, "ToolTip.Tip=\"{Binding DataPreviewSourceText}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding PreviewSelectedNodeText}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding PreviewSelectedWorkflowNodeCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding RunText}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding StartSelectedWorkflowCommand}\"");
        StringAssert.Contains(xaml, "ToolTip.Tip=\"{Binding WorkflowRunGuardText}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsDataPreviewBusy}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DataPreviewMessage}\"");
        StringAssert.Contains(xaml, "TextTrimming=\"CharacterEllipsis\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DataPreviewErrorMessage}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding HasDataPreviewError}\"");
        StringAssert.Contains(xaml, "MinHeight=\"96\"");
        StringAssert.Contains(xaml, "MaxHeight=\"220\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding DataPreviewColumns}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding DataPreviewRows}\"");
        StringAssert.Contains(xaml, "x:DataType=\"vm:TableDataPreviewColumnViewModel\"");
        StringAssert.Contains(xaml, "x:DataType=\"vm:TableDataPreviewRowViewModel\"");
        StringAssert.Contains(xaml, "x:DataType=\"vm:TableDataPreviewCellViewModel\"");
        StringAssert.Contains(xaml, "MinHeight=\"172\"");
        StringAssert.Contains(xaml, "RowDefinitions=\"Auto,Auto,*\"");
        Assert.IsFalse(nodeListXaml.Contains("DataPreview", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowEditorViewShowsRestoreBeforeValidateAndSave()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowEditorView.axaml");

        StringAssert.Contains(xaml, "Content=\"{Binding RestoreText}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding RestoreWorkflowDefinitionDraftCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding ValidateText}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding ValidateWorkflowDefinitionDraftCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding SaveText}\"");
        StringAssert.Contains(xaml, "Command=\"{Binding SaveWorkflowDefinitionDraftCommand}\"");

        var restoreIndex = xaml.IndexOf("Content=\"{Binding RestoreText}\"", StringComparison.Ordinal);
        var validateIndex = xaml.IndexOf("Content=\"{Binding ValidateText}\"", StringComparison.Ordinal);
        var saveIndex = xaml.IndexOf("Content=\"{Binding SaveText}\"", StringComparison.Ordinal);
        Assert.IsTrue(
            restoreIndex >= 0 && validateIndex > restoreIndex && saveIndex > validateIndex,
            "The draft restore button should appear before validate and save.");
    }

    [TestMethod]
    public void WorkflowListViewDoesNotHostRunButton()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowListView.axaml");

        Assert.IsFalse(xaml.Contains("Content=\"{Binding RunText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            xaml.Contains("Command=\"{Binding StartSelectedWorkflowCommand}\"", StringComparison.Ordinal));
    }

    [TestMethod]
    public void ConnectionsSectionIsCollapsedBehindToggleByDefault()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Content=\"{Binding ShowConnectionsText}\"");
        StringAssert.Contains(
            xaml,
            "IsChecked=\"{Binding IsWorkflowConnectionsAdvancedVisible, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "IsVisible=\"{Binding IsWorkflowConnectionsAdvancedVisible}\"");
        Assert.IsFalse(xaml.Contains("IsWorkflowConnectionsAdvancedVisible = true", StringComparison.Ordinal));
    }

    [TestMethod]
    public void MiddleColumnLayoutKeepsStructuredEditAreasCompactAndScrollable()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "<ScrollViewer VerticalScrollBarVisibility=\"Auto\"");
        StringAssert.Contains(xaml, "<StackPanel Spacing=\"10\">");
        StringAssert.Contains(xaml, "MaxHeight=\"140\"");
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,*\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,Auto,Auto,Auto\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,Auto\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("MinHeight=\"100\"", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowSummaryViewHostsAddNodePanelAboveNodeConfig()
    {
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");
        var nodeListXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");

        var openCommandIndex = summaryXaml.IndexOf(
            "Command=\"{Binding OpenWorkflowAddNodePanelCommand}\"",
            StringComparison.Ordinal);
        var panelIndex = summaryXaml.IndexOf(
            "<workflow:WorkflowAddNodeView IsVisible=\"{Binding IsWorkflowAddNodePanelVisible}\"/>",
            StringComparison.Ordinal);
        var configIndex = summaryXaml.IndexOf(
            "<workflow:WorkflowSelectedNodeConfigView />",
            StringComparison.Ordinal);

        Assert.AreNotEqual(
            -1,
            openCommandIndex,
            "The middle column should expose the add-node panel entry.");
        Assert.AreNotEqual(
            -1,
            panelIndex,
            "The middle column should host the inline add-node panel.");
        Assert.AreNotEqual(
            -1,
            configIndex,
            "The middle column should still host the selected node config panel.");
        Assert.IsTrue(
            openCommandIndex < panelIndex && panelIndex < configIndex,
            "The add-node entry and panel should stay above selected node configuration.");
        Assert.IsFalse(
            nodeListXaml.Contains("OpenWorkflowAddNodePanelCommand", StringComparison.Ordinal),
            "The node management column should not host add-node controls.");
        Assert.IsFalse(
            nodeListXaml.Contains("<workflow:WorkflowAddNodeView", StringComparison.Ordinal),
            "The node management column should not host the add-node panel.");
    }

    [TestMethod]
    public void WorkflowSummaryViewHostsRecentEventsBelowConnections()
    {
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");
        var recentEventsXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowRecentEventsView.axaml");

        var connectionsIndex = summaryXaml.IndexOf(
            "Text=\"{Binding ConnectionsSectionText}\"",
            StringComparison.Ordinal);
        var recentEventsIndex = summaryXaml.IndexOf(
            "<workflow:WorkflowRecentEventsView />",
            StringComparison.Ordinal);

        Assert.AreNotEqual(-1, connectionsIndex);
        Assert.AreNotEqual(-1, recentEventsIndex);
        Assert.IsGreaterThan(
            connectionsIndex,
            recentEventsIndex,
            "Recent events should sit below the connections section in the middle column.");
        StringAssert.Contains(recentEventsXaml, "Text=\"{Binding RecentEventsSectionText}\"");
        StringAssert.Contains(recentEventsXaml, "ItemsSource=\"{Binding VisibleRecentEvents}\"");
        StringAssert.Contains(
            recentEventsXaml,
            "IsChecked=\"{Binding IsRecentEventsExpanded, Mode=TwoWay}\"");
        StringAssert.Contains(
            recentEventsXaml,
            "Command=\"{Binding ViewAllRecentEventsCommand}\"");
    }

    private static string ReadSourceFile(params string[] pathParts)
    {
        var repoRoot = GetRepoRoot();
        return File.ReadAllText(Path.Combine(pathParts.Prepend(repoRoot).ToArray()));
    }

    private static int CountOccurrences(string value, string pattern)
    {
        var count = 0;
        var index = 0;
        while ((index = value.IndexOf(pattern, index, StringComparison.Ordinal)) >= 0)
        {
            count++;
            index += pattern.Length;
        }

        return count;
    }

    private static string GetRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI"))
                && Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI.Tests")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate FlowWeaver repository root.");
    }
}
